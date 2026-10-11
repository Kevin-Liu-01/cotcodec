#!/usr/bin/env python3
"""S2 v3 Phase 0 doctor (orx cpu-doctor node): the registered render oracle over the captured cells.

Runs on the development Mac, CPU only, model-free. Inputs: one capture directory written by
``harness/s2_locale/capture.py`` in the host's CPU lane (Slurm job 1131 for the 106-task sweep),
copied read-only into the scratchpad, and the capture's committed manifest. The screenshots and
saved documents stay out of the repository (public-repo hygiene); the doctor checks every file
against the committed manifest's SHA-256 before it reads anything, so it judges exactly the
captured data.

Cases:
  c01 manifest: every captured file matches the committed manifest (and the capture record names
      the code the job ran, which must equal this checkout's harness/s2_locale files);
  c02 gate semantics on synthetic fixtures: O3 accepts a reflected widget and rejects a shifted
      one, O2 rejects a bidi-reordered run, O5 passes an unchanged document, flags a mirrored one
      and a changed one;
  c03 calibration on the 17 dev tasks (tolerances, VCL coordinate offset, mirror specification);
  c04 I1 positive controls (synthetic plants in every application; in-application document plant);
  c05 I2 O6 invisibility (en-LTR equals stock);
  c06 I3 O1 text structure;
  c07 I4 O4 order under text swap;
  c08 I5 P7 one layout treatment (language-default RTL equals key RTL);
  c09 I6 A/A determinism;
  c10 K0 admission count >= 62 (intention to treat, agent-independent failures only);
  c11 in-application coupled-string plant (PCL-PCR) flagged by O2 where its field is visible;
  c12 catalogs: matched length on every generated string; Arabic share of visible chrome;
  c13 (reported, not in the committed gate) admission under the registration's checker-based
      semantics (P0.8b, P0.9): a cell excludes a task only if it changes the checker's verdict on
      the task's gold or do-nothing end state saved in that cell (--gold-verdicts, Slurm 1139-1140).
Status: PHASE0_K0_PASS when c01-c10 pass (the rules committed before the sweep), else PHASE0_K0_FAIL.

Usage: python scripts/run_s2v3_phase0_doctor.py --captures <dir> --manifest <committed manifest.json>
       --pool <pool-v3.json> --records-out <per-task json> --output <receipt json> [--workers 8]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.s2_locale import oracle as O  # noqa: E402
from harness.s2_locale import phase0 as P  # noqa: E402


def jdefault(o):
    if hasattr(o, "item"):
        return o.item()
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_manifest(cap: Path, manifest: dict) -> dict:
    bad, missing = [], []
    for rel, digest in manifest.items():
        p = cap / rel
        if not p.is_file():
            missing.append(rel)
        elif sha_file(p) != digest:
            bad.append(rel)
    extra = [str(p.relative_to(cap)) for p in cap.rglob("*") if p.is_file()
             and str(p.relative_to(cap)) not in manifest and p.name not in ("manifest.json", "receipt-1131.json")]
    return {"files": len(manifest), "mismatched": bad[:20], "missing": missing[:20], "n_mismatched": len(bad),
            "n_missing": len(missing), "unlisted": extra[:20], "pass": not bad and not missing}


def synthetic_semantics() -> dict:
    """Gate semantics on synthetic fixtures (no captured data)."""
    rng = np.random.default_rng(42)
    W, H = 400, 120
    img = np.full((H, W, 3), 245, dtype=np.int16)
    # a "widget": a dark glyph-like pattern at x=40..80, y=20..36
    glyph = (rng.random((16, 40)) > 0.6).astype(np.int16) * 200
    img[20:36, 40:80] = 245 - glyph[..., None]
    node = {"path": [0, 0], "role": "label", "name": "Fixture", "box": [36, 16, 48, 24], "showing": True}
    frame = (0, 0, W, H)
    mirrored = np.full_like(img, 245)
    mirrored[20:36, W - 80:W - 40] = img[20:36, 40:80]
    shifted = np.full_like(img, 245)
    shifted[20:36, W - 80 + 12:W - 40 + 12] = img[20:36, 40:80]
    r_ok = O.element_pass(img, mirrored, [node], frame, "reflect", 0.02, tol3=4)[0]
    r_sh = O.element_pass(img, shifted, [node], frame, "reflect", 0.02, tol3=4)[0]
    # O2: reorder halves of a text run
    reord = mirrored.copy()
    a = img[20:36, 40:60].copy()
    b = img[20:36, 60:80].copy()
    reord[20:36, W - 80:W - 60] = b
    reord[20:36, W - 60:W - 40] = a
    r_ro = O.element_pass(img, reord, [node], frame, "reflect", 0.02, tol3=4)[0]
    # O5 on a synthetic "document"
    doc = np.full((300, 600, 3), 255, dtype=np.int16)
    doc[50:250, 50:550] = 255 - ((rng.random((200, 500)) > 0.97) * 200)[..., None]
    box = [60, 60, 400, 150]
    same = doc.copy()
    flipped = doc.copy()
    flipped[60:210, 60:460] = doc[60:210, 60:460][:, ::-1]
    changed = doc.copy()
    changed[100:112, 100:150] = 0
    v_same = O.o5(doc, same, box, 50)["verdict"]
    v_flip = O.o5(doc, flipped, box, 50)["verdict"]
    v_chg = O.o5(doc, changed, box, 50)["verdict"]
    res = {"o3_reflected_accepted": bool(r_ok["at_expected"]), "o3_shifted_rejected": not r_sh["at_expected"],
           "o2_reordered_rejected": not r_ro.get("run", {}).get("identical", True),
           "o2_reflected_run_identical": bool(r_ok.get("run", {}).get("identical")),
           "o5_same": v_same, "o5_flipped": v_flip, "o5_changed": v_chg}
    res["pass"] = (res["o3_reflected_accepted"] and res["o3_shifted_rejected"] and res["o2_reordered_rejected"]
                   and res["o2_reflected_run_identical"] and v_same == "pass" and v_flip == "fail_mirrored"
                   and v_chg.startswith("fail"))
    return res


_G: dict = {}


def _init(cap, tol, pool):
    _G.update(cap=Path(cap), tol=tol, pool=pool)


def _one(args):
    task, cells = args
    rng = np.random.default_rng([42, int(task[:8], 16)])
    r = P.analyse_task(_G["cap"], task, cells, _G["tol"], _G["pool"][task], rng)
    raw = r.pop("_elements_raw")
    # keep a compact per-element record for the PCL-PCR plant and the O8 inventory
    r["plant_pcl_pcr_runs"] = [
        {"role": e["role"], "name": e["name"][:40], "ink_box": e["ink_box"], "run": e.get("run")}
        for e in raw.get("PCL-PCR", []) if e["text_run"] and not e.get("run", {}).get("identical")]
    r["o8_elements"] = [
        {"role": e["role"], "name": e["name"][:40], "dx": e.get("dx"), "found_mismatch": e["found_mismatch"],
         "clipped": e["clipped"], "intact": e["intact"], "at_expected": e["at_expected"]}
        for e in raw.get("E-ER", []) if not e["at_expected"]]
    return json.loads(json.dumps(r, default=jdefault))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--captures", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--capture-record", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--records-out", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--gold-verdicts", default=None, help="checker verdicts on the cells' saved golds (JSONL)")
    args = ap.parse_args()
    t0 = time.time()
    cap = Path(args.captures)
    manifest = json.loads(Path(args.manifest).read_text())
    caprec = json.loads(Path(args.capture_record).read_text())
    cases = {}
    c01 = check_manifest(cap, manifest)
    here = {n: sha_file(ROOT / "harness" / d / n) for n, d in
            (("capture.py", "s2_locale"), ("catalog.py", "s2_locale"), ("reachability.py", "q2_mutation"))}
    c01["code_sha256_capture_job"] = caprec.get("code_sha256")
    c01["code_sha256_checkout"] = here
    c01["code_matches"] = caprec.get("code_sha256") == here
    c01["pass"] = c01["pass"] and c01["code_matches"]
    cases["c01_manifest"] = c01
    cases["c02_gate_semantics"] = synthetic_semantics()
    pool = {t["task_id"]: t for t in json.loads(Path(args.pool).read_text())["tasks"]}
    recs = P.load_records(cap)
    dev = sorted(t for t in recs if pool[t]["split"] == "dev")
    tol = P.calibrate(cap, recs, dev)
    cases["c03_calibration"] = {"dev_tasks": len(dev), **tol, "pass": len(dev) == 17}
    tasks = sorted(recs)
    print(f"[{time.time() - t0:7.1f}s] manifest and calibration done; {len(tasks)} tasks", file=sys.stderr, flush=True)
    per_task = []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init, initargs=(str(cap), tol, pool)) as ex:
        for i, r in enumerate(ex.map(_one, [(t, recs[t]) for t in tasks])):
            per_task.append(r)
            if (i + 1) % 10 == 0:
                print(f"[{time.time() - t0:7.1f}s] {i + 1} tasks", file=sys.stderr, flush=True)
    dec = P.decide(per_task, tol)
    ic = dec["instrument_checks"]
    cases["c04_positive_controls"] = ic["I1_positive_controls"]
    cases["c05_o6_invisibility"] = ic["I2_o6_invisibility"]
    cases["c06_o1_text_structure"] = ic["I3_o1_text_structure"]
    cases["c07_o4_order"] = ic["I4_o4_order"]
    cases["c08_p7_one_layout_treatment"] = ic["I5_p7_one_layout_treatment"]
    cases["c09_aa_determinism"] = ic["I6_aa_determinism"]
    cases["c10_k0_admission"] = {"admitted": dec["admitted"], "K_min": dec["K_min"], "excluded": dec["excluded"],
                                 "exclusion_reasons": dec["exclusion_reasons"], "pass": dec["admitted"] >= dec["K_min"]}
    pcl = [r for r in per_task if r["split"] == "dev"]
    flagged = [r["task_id"][:8] for r in pcl if any(
        isinstance(x.get("run"), dict) and x["run"].get("mismatch") is not None and not x["run"]["identical"]
        for x in r["plant_pcl_pcr_runs"])]
    cases["c11_coupled_string_plant"] = {"dev_tasks": len(pcl), "flagged_by_o2": len(flagged), "tasks": flagged,
                                         "pass": len(flagged) == len(pcl)}
    cat = json.loads((cap / "catalog-stats.json").read_text())
    shares = [r["chrome"]["A"]["arabic"] / r["chrome"]["A"]["named"] for r in per_task
              if r.get("chrome", {}).get("A", {}).get("named")]
    cov = [r["chrome"]["coverage"]["share"] for r in per_task if r.get("chrome", {}).get("coverage", {}).get("share") is not None]
    cases["c12_catalogs"] = {"matched_length_all": cat.get("matched_length_all"), "mo_entries": cat.get("mo_entries"),
                             "registry_ar_values": cat.get("registry_ar_values"),
                             "arabic_chrome_share_median": round(float(np.median(shares)), 4) if shares else None,
                             "arabic_chrome_share_min": round(float(np.min(shares)), 4) if shares else None,
                             "tagged_covered_share_median": round(float(np.median(cov)), 4) if cov else None,
                             "pass": bool(cat.get("matched_length_all"))}
    ci = None
    if args.gold_verdicts:
        verdicts = [json.loads(x) for x in Path(args.gold_verdicts).read_text().splitlines() if x.strip()]
        ci = P.decide_checker_invariance(per_task, verdicts)
        cases["c13_checker_invariance_admission"] = {
            "admitted": ci["admitted"], "K_min": ci["K_min"], "reasons": ci["reasons"],
            "admitted_by_app": ci["admitted_by_app"], "verdict_rows": len(verdicts),
            "pass": ci["admitted"] >= ci["K_min"], "in_committed_gate": False}
    gate = all(cases[k]["pass"] for k in ("c01_manifest", "c02_gate_semantics", "c03_calibration",
                                         "c04_positive_controls", "c05_o6_invisibility", "c06_o1_text_structure",
                                         "c07_o4_order", "c08_p7_one_layout_treatment", "c09_aa_determinism",
                                         "c10_k0_admission"))
    status = "PHASE0_K0_PASS" if gate else "PHASE0_K0_FAIL"
    admitted_ids = sorted(r["task_id"] for r in per_task if r["admitted"])
    Path(args.records_out).write_text(json.dumps({"schema": "s2v3-phase0-oracle-v1", "tolerances": tol,
                                                  "decision": dec, "admitted_task_ids": admitted_ids,
                                                  "checker_invariance": ci,
                                                  "tasks": per_task}, indent=1, default=jdefault, ensure_ascii=False))
    receipt = {"doctor": "s2v3-phase0-render-oracle", "status": status,
               "evidence_grade": ("CPU_LANE_CONTAINER_CAPTURE: the certified VM's LibreOffice 7.3.7.2 userland in a "
                                  "container (Xvfb, openbox) with generated pseudo-Arabic and tagged catalogs; not the "
                                  "derived image, not the VM lane, not the shipped Arabic catalogs. K1 (the D53 delta "
                                  "certification) is not decided here."),
               "cases": {k: {**v, "status": "PASS" if v.get("pass") else "FAIL"} for k, v in cases.items()},
               "k0": dec["K0"], "admitted": dec["admitted"], "candidates": dec["K_candidates"],
               "admitted_checker_invariance": ci["admitted"] if ci else None,
               "records_out": str(args.records_out), "records_sha256": sha_file(Path(args.records_out)),
               "manifest_sha256": sha_file(Path(args.manifest)), "elapsed_seconds": round(time.time() - t0, 1)}
    Path(args.output).write_text(json.dumps(receipt, indent=1, default=jdefault, ensure_ascii=False))
    print(json.dumps({"status": status, "k0": dec["K0"], "admitted": dec["admitted"],
                      "admitted_checker_invariance": ci["admitted"] if ci else None,
                      "cases": {k: v["status"] for k, v in receipt["cases"].items()}}, indent=1))
    # exit 0 when the doctor ran validly (inputs verified, gates semantically sound, calibration
    # complete); the K0 verdict itself is the receipt's status
    valid = all(cases[k]["pass"] for k in ("c01_manifest", "c02_gate_semantics", "c03_calibration"))
    return 0 if valid else 1


if __name__ == "__main__":
    sys.exit(main())
