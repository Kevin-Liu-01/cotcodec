#!/usr/bin/env python3
"""Validate the S2 render oracle on fixtures with known properties (D68 repair).

Runs oracle.py's checks on every fixture variant rendered by fixture.mjs, computes the A/A
mismatch (the isolated variant rendered twice), and compares each check's verdict with the
verdict the variant was built to produce. The oracle is valid on this fixture only if every
expected verdict is observed: the clean decoupled variants pass every check, the coupled
variant fails O2 (bidi leak) and nothing else, and each negative control fails exactly its
target check.

Usage: python validate.py <render_dir> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oracle  # noqa: E402

EXPECTED = {
    "coupled": {"O1_structure": True, "O2_text_run_identity": False, "O3_mirror_fidelity": True, "O4_order_under_text_swap": True, "O5_content_identity": True},
    "isolated": {"O1_structure": True, "O2_text_run_identity": True, "O3_mirror_fidelity": True, "O4_order_under_text_swap": True, "O5_content_identity": True},
    "plaintext": {"O1_structure": True, "O2_text_run_identity": True, "O3_mirror_fidelity": True, "O4_order_under_text_swap": True, "O5_content_identity": True},
    "halfmirror": {"O1_structure": True, "O2_text_run_identity": True, "O3_mirror_fidelity": False, "O4_order_under_text_swap": True, "O5_content_identity": True},
    "reorder": {"O1_structure": True, "O2_text_run_identity": True, "O3_mirror_fidelity": True, "O4_order_under_text_swap": False, "O5_content_identity": True},
    "drift": {"O1_structure": True, "O2_text_run_identity": True, "O3_mirror_fidelity": True, "O4_order_under_text_swap": True, "O5_content_identity": False},
    "composite": {"O1_structure": True, "O2_text_run_identity": False, "O3_mirror_fidelity": True, "O4_order_under_text_swap": True, "O5_content_identity": True},
}


def aa(render_dir: Path, tol, suffix):
    """Worst O2 mismatch between the isolated variant and a second render of it (suffix -AA:
    identical render; -AAshift: the window moved by 0.37 px, another subpixel phase)."""
    worst, n, worst_name = 0.0, 0, ""
    for cell in oracle.CELLS:
        img1, el1 = oracle.load(render_dir / f"isolated-{cell}.png", render_dir / f"isolated-{cell}.json")
        img2, el2 = oracle.load(render_dir / f"isolated-{cell}{suffix}.png", render_dir / f"isolated-{cell}{suffix}.json")
        i2 = {e["path"]: e for e in el2["elements"]}
        for e in el1["elements"]:
            if not e.get("text"):
                continue
            m1 = oracle.ink_mask(img1, e["box"], tol["ink_threshold"])
            m2 = oracle.ink_mask(img2, i2[e["path"]]["box"], tol["ink_threshold"])
            mis, _ = oracle.mask_mismatch(m1, m2, tol["o2_dim_px"])
            if mis > worst:
                worst, worst_name = mis, e["name"].strip("\u2068\u2069")
            n += 1
    return {"runs_compared": n, "max_mismatch": round(worst, 4), "worst_run": worst_name}


def main() -> int:
    rd = Path(sys.argv[1])
    tol = dict(oracle.DEFAULT_TOL)
    # A/A first; the O2 tolerance is fixed from it before any variant is judged:
    # max(0.02, 2 x the worst shifted-A/A mismatch)
    aa_same = aa(rd, tol, "-AA")
    aa_shift = aa(rd, tol, "-AAshift")
    tol["o2_mismatch"] = round(max(0.02, 2 * aa_shift["max_mismatch"], 2 * aa_same["max_mismatch"]), 4)
    result = {"tolerance": tol, "tolerance_rule": "o2_mismatch = max(0.02, 2 x worst A/A mismatch), fixed before variants are judged", "aa": {"same": aa_same, "shift_0.37px": aa_shift}, "variants": {}}
    ok = True
    for variant, exp in EXPECTED.items():
        cells = {c: [str(rd / f"{variant}-{c}.png"), str(rd / f"{variant}-{c}.json")] for c in oracle.CELLS}
        st = oracle.check_state(variant, cells, tol)
        obs = {k: v["pass"] for k, v in st["checks"].items()}
        match = obs == exp
        ok &= match
        leaks = st["checks"]["O2_text_run_identity"]["leaks"]
        result["variants"][variant] = {
            "expected": exp,
            "observed": obs,
            "as_expected": match,
            "o2_runs_checked": st["checks"]["O2_text_run_identity"]["runs_checked"],
            "o2_leaks": [{"pair": l["pair"], "name": l["name"].replace("⁨", "<FSI>").replace("⁩", "<PDI>"), "mismatch": l["mismatch"]} for l in leaks],
            "o3_violations": len(st["checks"]["O3_mirror_fidelity"]["violations"]),
            "o3_units_checked": st["checks"]["O3_mirror_fidelity"]["units_checked"],
            "o4_violations": st["checks"]["O4_order_under_text_swap"]["violations"],
            "o5": st["checks"]["O5_content_identity"],
        }
    result["all_as_expected"] = ok
    bj = rd / "browser.json"
    result["renderer"] = json.loads(bj.read_text()) if bj.exists() else None
    result["render_inputs_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(rd.glob("*.png")) + sorted(rd.glob("*.json")) if p.name != "browser.json"}
    Path(sys.argv[2]).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    leaks_c = [l["mismatch"] for l in result["variants"]["coupled"]["o2_leaks"]]
    result["coupled_min_leak_mismatch"] = min(leaks_c) if leaks_c else None
    Path(sys.argv[2]).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"all_as_expected": ok, "aa": result["aa"], "tol": tol["o2_mismatch"], "per_variant": {v: r["as_expected"] for v, r in result["variants"].items()}, "coupled_leaks": [l["name"] + " " + l["pair"] for l in result["variants"]["coupled"]["o2_leaks"]], "composite_leaks": [l["name"] + " " + l["pair"] for l in result["variants"]["composite"]["o2_leaks"]]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
