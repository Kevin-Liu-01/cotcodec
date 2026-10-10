#!/usr/bin/env python3
"""Merge the per-process outputs of instrument_sim.py into compute/instrument-sim.json with a summary.

The simulation ran as 30 processes on the development Mac (one per seed and
part, and per language or noise condition): gates-<seed>.json (PBD and A11
gates, convention gate), uot-<seed>-<lang>.json (the legacy UOT instrument),
oc2-<seed>-<condition>.json (operating characteristics with the registered
rule), calibration.json, and oc-<seed>.json (the first operating-characteristics
run, before the registered rule existed; kept as superseded evidence).

Usage: merge_sim.py <dir-with-process-outputs> <out.json>
"""

from __future__ import annotations

import glob
import hashlib
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text())


def main() -> int:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    files = sorted(glob.glob(str(src / "*.json")))
    inputs = {Path(f).name: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files}
    gates = [g for s in (42, 43, 44) for g in load(str(src / f"gates-{s}.json"))["pbd_a11_gates"]]
    uot = [g for s in (42, 43, 44) for lang in ("zh", "pl") for g in load(str(src / f"uot-{s}-{lang}.json"))["uot_gates"]]
    oc2 = [o for f in sorted(glob.glob(str(src / "oc2-*.json"))) for o in load(f)["oc"]]
    oc1 = [o for s in (42, 43, 44) for o in load(str(src / f"oc-{s}.json"))["oc"]]
    cal = load(str(src / "calibration.json"))["calibration"]

    # ---- PBD gate summary
    bern = [r for g in gates for r in g["rows"] if r["system"].startswith("bernoulli")]
    perm = [r["pbd_permuted_alignment_A"] for g in gates for r in g["rows"]]
    true_cut = [r for g in gates for r in g["rows"] if r["system"] == "true_cuts_displaced_0.00"]
    self_vs_truth = [abs(r["S_pbd_selfA"] - r["S_pbd_truth"]) for g in gates for r in g["rows"]
                     if r["S_pbd_selfA"] == r["S_pbd_selfA"] and r["S_pbd_truth"] == r["S_pbd_truth"]
                     and not r["system"].startswith("every_char")]
    rho = {}
    for g in gates:
        for r in g["rows"]:
            if r["system"].startswith("gauss_rho"):
                rho.setdefault((g["seed"], g["lang"]), []).append((float(r["system"][9:]), r["S_pbd_selfA"]))
    monotone = all(all(b[1] > a[1] for a, b in zip(sorted(v), sorted(v)[1:])) for v in rho.values())
    a11_norm = [r["S_a11_xfit"] for g in gates for r in g["rows"] if r["S_a11_xfit"] is not None]
    word = [r["S_pbd_selfA"] for g in gates for r in g["rows"] if r["system"] == "word_gaps_both_sides"]
    conv = [g["convention"] for g in gates]
    summary = {
        "pbd_bernoulli_abs_S_self_max": round(max(abs(r["S_pbd_selfA"]) for r in bern), 4),
        "pbd_bernoulli_rates": sorted({r["system"] for r in bern}),
        "pbd_permuted_alignment_max": round(max(perm), 4),
        "pbd_true_cut_system_raw_range": [round(min(r["pbd_raw_A"] for r in true_cut), 4), round(max(r["pbd_raw_A"] for r in true_cut), 4)],
        "pbd_S_self_minus_truth_abs_max": round(max(self_vs_truth), 4),
        "pbd_monotone_in_rho_all_seed_lang": monotone,
        "a11_normalized_range": [round(min(a11_norm), 4), round(max(a11_norm), 4)],
        "word_reference_S_self_range": [round(min(word), 4), round(max(word), 4)],
        "convention_end_vs_start_abs_diff_max": max(c["abs_difference_end_vs_start"] for c in conv),
        "convention_round_trip_identity_min": min(min(c["round_trip_identity_share"]["end"], c["round_trip_identity_share"]["start"]) for c in conv),
        "plus1_byte_abs_diff_max": max(c["abs_difference_plus1_vs_canonical"] for c in conv),
        "inter_aligner_cut_dice_gates": {g["lang"]: [x["inter_aligner_cut_dice"] for x in gates if x["lang"] == g["lang"]] for g in gates},
    }
    # ---- UOT summary
    rows = [(g["lang"], r) for g in uot for r in g["rows"]]
    ratios = [r["aligned_over_permuted"] for _, r in rows if r["aligned_over_permuted"] is not None]
    tco = [r["aligned_over_permuted"] for _, r in rows if r["system"] == "true_cut_oracle"]
    s_self = [r["S_uot_self"] for _, r in rows]
    undefined_zh = sum(1 for lang, r in rows if lang == "zh" and r["S_uot_self"] is None)
    total_zh = sum(1 for lang, _ in rows if lang == "zh")
    pl_s = [r["S_uot_self"] for lang, r in rows if lang == "pl" and r["S_uot_self"] is not None]
    conv_pl = [r["convention_loss_ratio"] for lang, r in rows if lang == "pl" and r["convention_loss_ratio"] is not None]
    perfect = [r["uot_aligned"] for _, r in rows if r["system"] == "true_cut_oracle"]
    wordgap = [r["uot_aligned"] for _, r in rows if r["system"] == "word_gaps_both_sides"]
    summary.update({
        "uot_pairs_total": sum(g["pairs"] for g in uot),
        "uot_aligned_over_permuted_range_all_systems": [min(ratios), max(ratios)],
        "uot_aligned_over_permuted_range_true_cut_system": [min(tco), max(tco)],
        "uot_S_self_undefined_zh_cells": f"{undefined_zh} of {total_zh}",
        "uot_S_self_range_pl": [min(pl_s), max(pl_s)],
        "uot_chunk_start_convention_loss_ratio_range_pl": [min(conv_pl), max(conv_pl)],
        "uot_loss_true_cut_system_range": [min(perfect), max(perfect)],
        "uot_loss_word_gaps_range": [min(wordgap), max(wordgap)],
        "uot_s_self_values_count": len(s_self),
    })
    # ---- OC summary table (registered rule), means over seeds
    table = {}
    for o in oc2:
        key = f'{o["lang"]}-{o["aligner_noise"]}'
        for r in o["rows"]:
            cell = table.setdefault(key, {}).setdefault(str(r["displaced_fraction"]), {"S_true": [], "S_self": [], "sd": [], "agree": [],
                                                                                         "NH": [], "H": [], "I": [], "INV": [],
                                                                                         "lit_NH": [], "lit_H": []})
            cell["S_true"].append(r["S_true"])
            cell["S_self"].append(r["S_pop_A_selfA"])
            cell["sd"].append(r["sd_of_estimate_self"])
            cell["agree"].append(o["inter_aligner_cut_dice"])
            cell["NH"].append(r["registered:NO_HEADROOM"])
            cell["H"].append(r["registered:HEADROOM"])
            cell["I"].append(r["registered:INDETERMINATE"])
            cell["INV"].append(r["registered:INSTRUMENT_INVALID"])
            cell["lit_NH"].append(r["dossier_literal:NO_HEADROOM"])
            cell["lit_H"].append(r["dossier_literal:HEADROOM"])
    oc_table = {k: {f: {m: round(sum(v) / len(v), 4) for m, v in cell.items()} for f, cell in d.items()} for k, d in table.items()}
    wrong_nh = [(k, f, c["S_true"], c["NH"]) for k, d in oc_table.items() for f, c in d.items() if c["S_true"] < 0.90 and c["NH"] > 0]
    wrong_h = [(k, f, c["S_true"], c["H"]) for k, d in oc_table.items() for f, c in d.items() if c["S_true"] >= 0.90 and c["H"] > 0]
    lit_wrong_h = [(k, f, c["S_true"], c["lit_H"]) for k, d in oc_table.items() for f, c in d.items() if c["S_true"] >= 0.90 and c["lit_H"] > 0]
    summary.update({
        "oc_registered_wrong_side_NO_HEADROOM": wrong_nh,
        "oc_registered_wrong_side_HEADROOM": wrong_h,
        "oc_dossier_literal_wrong_side_HEADROOM": lit_wrong_h,
        "oc_sd_of_estimate_max": max(c["sd"] for d in oc_table.values() for c in d.values()),
    })
    merged = {
        "script": "instrument_sim.py (merged by merge_sim.py)",
        "inputs_sha256": inputs,
        "summary": summary,
        "oc_registered_table": oc_table,
        "pbd_a11_gates": gates,
        "uot_gates": uot,
        "oc_registered": oc2,
        "calibration": cal,
        "oc_first_run_superseded": {
            "note": "First operating-characteristics run (pool 6,000, three conditions), made before the registered rule existed; it compared the dossier-literal rule and a margin-only rule and showed the attenuation that led to the agreement-dependent registered rule. Kept, not used for the registered numbers.",
            "runs": oc1,
        },
    }
    out.write_text(json.dumps(merged, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
