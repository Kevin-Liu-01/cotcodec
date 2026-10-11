"""S2 v3 Phase 0: per-task oracle records, the admission rule (K0) and the instrument checks.

The rules below were fixed on 2026-10-11 before the full 106-task sweep ran (after a three-task
dev smoke and two debug jobs, which are development; registration v3.1 section "Phase 0 admission
(K0), intention to treat"). Admission excludes a task only for a failure no agent could get past,
observed in any Phase 1 cell (E, A, ER, AR) or in the placebo cell PL:

  A1 setup: the task's files are staged from the pinned cache and its document window opens;
  A2 title: the LibreOffice window title is byte-identical to the postconfig's activate_window
     target (O7), so the strict activation that precedes the checker's save succeeds;
  A3 save: the task's own postconfig save writes the result file;
  A4 file identity: the saved result file's parts (OOXML/ODF members, timestamps and rsids
     removed) equal the en-LTR cell's, ignoring any part that also differs between the two en-LTR
     replicates (E, E2), which is nondeterministic by construction;
  A5 content leak: no Arabic letter (A, AR) or KeyID tag (Q) in a saved result file that the
     en-LTR cell's file lacks.

O2, O3, O5 and O8 never exclude a task: they describe the treatment (mirror fidelity, clipped or
misplaced controls, document identity) and enter Phase 1 as moderators. The instrument checks
are global; each must hold for K0 to pass:

  I1 positive controls: in each application, every synthetic plant is detected (a shifted widget
     fails O3, a reordered text run fails O2, an altered document block fails O5), and the
     in-application document plant (PD) fails O5 where it planted;
  I2 O6 invisibility: E equals S within tol6 on at least 95% of tasks;
  I3 O1 text structure: E-A and ER-AR showing structures identical on at least 95% of tasks;
  I4 O4 order: sibling order agrees between E and A on at least 95% of compared parents;
  I5 P7: AD equals AR within tol6 on at least 95% of tasks;
  I6 A/A: E-E2 within tol6 on at least 95% of tasks (the render is deterministic enough for the
     step-0 check of Phase 1).

K0 passes if the admitted tasks number at least 62 and I1-I6 hold.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from harness.s2_locale import oracle as O

PHASE1_CELLS = ("E", "A", "ER", "AR")
K_MIN = 62
SHARE = 0.95
RNG_SEED = 42


def load_records(cap: Path) -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for line in (cap / "records.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["task_id"]][r["cell"]] = r
    return out


def a11y(cap: Path, task: str, cell: str) -> dict | None:
    p = cap / "a11y" / task / f"{cell}.json"
    return json.loads(p.read_text()) if p.is_file() else None


def shot(cap: Path, task: str, cell: str) -> np.ndarray | None:
    p = cap / "shots" / task / f"{cell}.png"
    return O.load_png(p) if p.is_file() else None


def saved_file(cap: Path, task: str, cell: str, rec: dict) -> list[Path]:
    d = cap / "saved" / task / cell
    return sorted(p for p in d.rglob("*") if p.is_file()) if d.is_dir() else []


# ------------------------------------------------------------------------------------------
# tolerances from the A/A replicates of the dev tasks


def _calib_dy(args) -> int | None:
    cap, t = args
    ie, de = shot(cap, t, "E"), a11y(cap, t, "E")
    if ie is None or not de:
        return None
    return O.estimate_dy(ie, O.showing_nodes(de))


def _calib_task(args) -> dict:
    cap, t, dy_vcl = args
    out = {"elem": [], "full": [], "doc": [], "trans": [], "dxs": []}
    for a, b in (("E", "E2"), ("ER", "ER2")):
        ia, ib = shot(cap, t, a), shot(cap, t, b)
        if ia is not None and ib is not None:
            out["full"].append(O.pixel_diff(ia, ib)["diff_pixels"])
    ie, de = shot(cap, t, "E"), a11y(cap, t, "E")
    if ie is None or not de:
        return out
    nodes = O.place_nodes(ie, O.showing_nodes(de), dy_vcl)
    fr = O.frame_box(nodes) or (0, 0, 1920, 1080)
    i2 = shot(cap, t, "E2")
    if i2 is not None:
        out["elem"] = [e["local_mismatch"] for e in O.element_pass(ie, i2, nodes, fr, "identity", 1.0)]
        box = O.doc_region(nodes)
        if box:
            al = O.align_count(ie, i2, box)
            if al.get("ok"):
                out["doc"].append(al["diff_pixels"])
    ipl = shot(cap, t, "PL")
    if ipl is not None:
        # translation noise: toolbar elements the shuffle moved within their row
        for e in O.element_pass(ie, ipl, nodes, fr, "identity", 0.25):
            if e["role"] in ("push button", "toggle button") and not e.get("unmoved") \
                    and e.get("found_y") is not None and abs(e["found_y"] - e["ink_box"][1]) <= 2 \
                    and e["found_mismatch"] <= 0.25:
                out["trans"].append(e["found_mismatch"])
    ier = shot(cap, t, "ER")
    if ier is not None:
        for e in O.element_pass(ie, ier, nodes, fr, "reflect", 0.25, tol3=24):
            if e["near_expected"] and e["local_mismatch"] <= 0.25:
                out["dxs"].append(abs(e["dx"]))
    return out


def calibrate(cap: Path, recs: dict, dev_tasks: list[str], executor=None) -> dict:
    """Tolerances and the VCL coordinate offset, from the 17 dev tasks only (frozen for the rest).
    ``executor`` (optional) maps the per-task work in parallel; the result does not depend on it."""
    mapper = executor.map if executor is not None else map
    dys = [d for d in mapper(_calib_dy, [(cap, t) for t in dev_tasks]) if d is not None]
    dy_vcl = int(Counter(dys).most_common(1)[0][0]) if dys else 0
    parts = list(mapper(_calib_task, [(cap, t, dy_vcl) for t in dev_tasks]))
    elem = [x for p in parts for x in p["elem"]]
    full = [x for p in parts for x in p["full"]]
    doc = [x for p in parts for x in p["doc"]]
    trans = [x for p in parts for x in p["trans"]]
    dxs = [x for p in parts for x in p["dxs"]]
    worst = max(elem) if elem else 0.0
    p95t = float(np.percentile(trans, 95)) if trans else 0.0
    tol2 = round(min(0.10, max(0.02, 2 * worst, p95t)), 4)
    tol3 = int(max(2, math.ceil(float(np.percentile(dxs, 95))))) if dxs else 2
    return {"dy_vcl": dy_vcl, "dy_vcl_by_dev_task": dys,
            "aa_elements": len(elem), "aa_worst_element_mismatch": round(worst, 4),
            "translation_elements": len(trans), "translation_p95_mismatch": round(p95t, 4), "tol2": tol2,
            "reflection_dx_elements": len(dxs), "tol3": tol3,
            "aa_full_diff_pixels": full, "tol6": int(max(50, 2 * max(full))) if full else 50,
            "aa_doc_diff_pixels": doc, "tol5": int(max(50, 2 * max(doc))) if doc else 50}


# ------------------------------------------------------------------------------------------
# synthetic plants


def plant_shift(img, el, dx=10):
    x, y = el["found_x"], el["found_y"]
    w, h = el["ink_box"][2], el["ink_box"][3]
    out = img.copy()
    patch = img[y:y + h, x:x + w].copy()
    bg = np.median(img[max(0, y - 2):y + h + 2, max(0, x - 2):x + w + 2].reshape(-1, 3), axis=0).astype(img.dtype)
    out[y:y + h, x:x + w] = bg
    if x + dx + w <= img.shape[1]:
        out[y:y + h, x + dx:x + dx + w] = patch
    return out


def plant_reorder(img, el):
    x, y = el["found_x"], el["found_y"]
    w, h = el["ink_box"][2], el["ink_box"][3]
    out = img.copy()
    half = w // 2
    left = img[y:y + h, x:x + half].copy()
    right = img[y:y + h, x + half:x + w].copy()
    out[y:y + h, x:x + (w - half)] = right
    out[y:y + h, x + (w - half):x + w] = left
    return out


def plant_doc(img, box, dx=0, dy=0, size=(48, 14)):
    x, y, w, h = box
    cx, cy = x + dx + w // 3, y + dy + h // 3
    out = img.copy()
    out[cy:cy + size[1], cx:cx + size[0]] = 255 - out[cy:cy + size[1], cx:cx + size[0]]
    return out


# ------------------------------------------------------------------------------------------


def analyse_task(cap: Path, task: str, cells: dict[str, dict], tol: dict, pool_task: dict, rng) -> dict:
    res: dict = {"task_id": task, "app": pool_task["app"], "split": pool_task["split"]}
    imgs = {c: shot(cap, task, c) for c in cells}
    dumps = {c: a11y(cap, task, c) for c in cells}
    nodes = {c: O.showing_nodes(d) if d else [] for c, d in dumps.items()}
    placed = {}
    for c in ("E", "A", "PCL"):
        if imgs.get(c) is not None and nodes.get(c):
            placed[c] = O.place_nodes(imgs[c], nodes[c], tol["dy_vcl"])
    expected = cells.get("E", {}).get("expected_title")
    # admission -------------------------------------------------------------------------
    adm_cells = [c for c in PHASE1_CELLS + ("PL",) if c in cells]
    reasons = []
    for c in adm_cells:
        r = cells[c]
        if r.get("error"):
            reasons.append(f"A1 render error in {c}")
            continue
        if any(s.get("type") == "download" and not s.get("cached") for s in r.get("setup_steps", [])):
            reasons.append(f"A1 download not cached in {c}")
        if expected and r.get("title_found") != expected:
            reasons.append(f"A2 title differs in {c}: {r.get('title_found')!r}")
        saves = [e for e in r.get("postconfig", {}).get("events", []) if "save" in e]
        if saves and not all(e.get("written") for e in saves):
            reasons.append(f"A3 postconfig save not written in {c}")
    titles = {c: cells[c].get("title_found") for c in cells if not cells[c].get("error")}
    res["titles_identical"] = len({t for c, t in titles.items() if c in adm_cells}) == 1
    # saved files ------------------------------------------------------------------------
    parts = {}
    for c in cells:
        files = saved_file(cap, task, c, cells[c])
        parts[c] = {f.name: O.canonical_parts(f) for f in files}
    noisy = set()
    if "E2" in parts:
        for name, pe in parts.get("E", {}).items():
            p2 = parts["E2"].get(name)
            if pe and p2:
                noisy |= {k for k in set(pe) | set(p2) if pe.get(k) != p2.get(k)}
    res["aa_noisy_parts"] = sorted(noisy)
    diffs = {}
    for c in cells:
        if c == "E":
            continue
        d = []
        for name, pe in parts.get("E", {}).items():
            pc = parts[c].get(name)
            if pe is None or pc is None:
                if pe is not None or pc is not None:
                    d.append(f"{name}: unreadable in one cell")
                continue
            d += [f"{name}:{k}" for k in sorted(set(pe) | set(pc)) if pe.get(k) != pc.get(k) and k not in noisy]
        diffs[c] = d
    res["saved_part_diffs_vs_E"] = {c: v[:8] for c, v in diffs.items() if v}
    for c in adm_cells:
        if c != "E" and diffs.get(c):
            reasons.append(f"A4 saved file differs in {c}: {diffs[c][:3]}")
    leaks = {}
    base_scan = {f.name: O.scan_text(f) for f in saved_file(cap, task, "E", cells.get("E", {}))}
    for c in ("A", "AR", "AD", "Q"):
        if c not in cells:
            continue
        for f in saved_file(cap, task, c, cells[c]):
            s = O.scan_text(f)
            b = base_scan.get(f.name, {})
            if s.get("arabic", 0) > b.get("arabic", 0) or s.get("tag", 0) > b.get("tag", 0):
                leaks.setdefault(c, []).append({"file": f.name, **s})
    res["content_leaks"] = leaks
    for c in ("A", "AR", "Q"):
        if leaks.get(c):
            reasons.append(f"A5 content leak in {c}")
    res["admission_reasons"] = reasons
    res["admitted"] = not reasons
    # O6, A/A and P7 ----------------------------------------------------------------------
    def full(a, b):
        if imgs.get(a) is None or imgs.get(b) is None:
            return None
        return O.pixel_diff(imgs[a], imgs[b])
    res["o6_E_vs_S"] = full("E", "S")
    res["aa_E_vs_E2"] = full("E", "E2")
    res["p7_AD_vs_AR"] = full("AD", "AR")
    res["aa_ER_vs_ER2"] = full("ER", "ER2")
    res["text_E_vs_A"] = full("E", "A")
    for k in ("o6_E_vs_S", "aa_E_vs_E2", "p7_AD_vs_AR", "aa_ER_vs_ER2"):
        if res[k] is not None:
            res[k]["pass"] = res[k]["diff_pixels"] <= tol["tol6"]
    # O1 structure ------------------------------------------------------------------------
    o1 = {}
    for a, b in (("E", "A"), ("ER", "AR"), ("E", "ER"), ("A", "AR"), ("E", "S"), ("E", "E2"), ("E", "PL"), ("E", "Q")):
        if nodes.get(a) and nodes.get(b):
            o1[f"{a}-{b}"] = O.structure_diff(nodes[a], nodes[b])
    res["o1"] = o1
    # O2/O3/O8 ----------------------------------------------------------------------------
    frame = O.frame_box(nodes.get("E") or []) or (0, 0, 1920, 1080)
    res["frame"] = list(frame)
    elems = {}
    for ltr, oth, mode in (("E", "ER", "reflect"), ("A", "AR", "reflect"), ("E", "PL", "identity"),
                           ("PCL", "PCR", "reflect")):
        if imgs.get(ltr) is None or imgs.get(oth) is None or not nodes.get(ltr):
            continue
        paths = {(tuple(n["path"]), n["role"]) for n in nodes.get(oth, [])}
        elems[f"{ltr}-{oth}"] = O.element_pass(imgs[ltr], imgs[oth], placed[ltr], frame, mode, tol["tol2"], paths,
                                               tol3=tol["tol3"] if mode == "reflect" else 2)
    res["elements"] = {k: summarize_elements(v) for k, v in elems.items()}
    res["_elements_raw"] = elems
    # O4 order --------------------------------------------------------------------------
    if nodes.get("E") and nodes.get("A"):
        bx = lambda ns: {tuple(n["path"]): n["box"][0] for n in O.leaf_elements(ns)}  # noqa: E731
        res["o4_ltr"] = O.order_agreement(O.sibling_order(bx(nodes["E"])), O.sibling_order(bx(nodes["A"])))
    if "E-ER" in elems and "A-AR" in elems:
        loc = lambda es: {tuple(e["path"]): e["found_x"] for e in es if e["intact"]}  # noqa: E731
        res["o4_rtl"] = O.order_agreement(O.sibling_order(loc(elems["E-ER"])), O.sibling_order(loc(elems["A-AR"])))
    # O5 ----------------------------------------------------------------------------------
    box = O.doc_region(placed.get("E") or [])
    res["doc_box"] = box
    o5 = {}
    if box is not None and imgs.get("E") is not None:
        for c in ("A", "ER", "AR", "PL", "E2", "PD"):
            if imgs.get(c) is not None:
                o5[c] = O.o5(imgs["E"], imgs[c], box, tol["tol5"], max_dy=260 if c == "PL" else 60)
    res["o5"] = o5
    # synthetic plants (positive controls) on ER --------------------------------------------
    plants = {}
    if "E-ER" in elems and imgs.get("ER") is not None:
        cand = [e for e in elems["E-ER"] if e["at_expected"] and e["ink_box"][2] >= 16]
        if cand:
            el = cand[int(rng.integers(len(cand)))]
            shifted = plant_shift(imgs["ER"], el, dx=tol["tol3"] + 8)
            node = next(n for n in placed["E"] if n["path"] == el["path"] and n["role"] == el["role"])
            r1 = O.element_pass(imgs["E"], shifted, [node], frame, "reflect", tol["tol2"], tol3=tol["tol3"])
            plants["o3_shift_detected"] = bool(r1) and not r1[0]["at_expected"]
            runs = [e for e in cand if e["text_run"] and e.get("run", {}).get("identical")]
            if runs:
                elr = runs[int(rng.integers(len(runs)))]
                noder = next(n for n in placed["E"] if n["path"] == elr["path"] and n["role"] == elr["role"])
                reordered = plant_reorder(imgs["ER"], elr)
                r2 = O.element_pass(imgs["E"], reordered, [noder], frame, "reflect", tol["tol2"], tol3=tol["tol3"])
                plants["o2_reorder_detected"] = bool(r2) and not r2[0].get("run", {}).get("identical", False)
            plants["element"] = {"role": el["role"], "name": el["name"][:40], "ink_w": el["ink_box"][2]}
        if box is not None and o5.get("ER", {}).get("unflipped", {}).get("ok"):
            u = o5["ER"]["unflipped"]
            changed = plant_doc(imgs["ER"], box, u["dx"], u["dy"])
            r3 = O.o5(imgs["E"], changed, box, tol["tol5"])
            plants["o5_doc_detected"] = r3["verdict"].startswith("fail")
    res["plants"] = plants
    # P0.13 Arabic chrome share and P0.8 coverage ------------------------------------------
    res["chrome"] = chrome_shares(nodes)
    return res


def summarize_elements(es: list[dict]) -> dict:
    n = len(es)
    if not n:
        return {"n": 0}
    runs = [e for e in es if e["text_run"]]
    by_role = defaultdict(lambda: [0, 0, 0, 0])
    for e in es:
        r = by_role[e["role"]]
        r[0] += 1
        r[1] += int(e["at_expected"])
        r[2] += int(e["intact"])
        r[3] += int(e.get("unmoved", False))
    disp = [abs(e.get("disp_x", 0)) + abs(e.get("disp_y", 0)) for e in es if e["intact"]]
    return {"n": n, "at_expected": sum(e["at_expected"] for e in es), "intact": sum(e["intact"] for e in es),
            "unmoved": sum(bool(e.get("unmoved")) for e in es), "clipped": sum(e["clipped"] for e in es),
            "missing": sum(1 for e in es if not e["intact"] and not e["clipped"]),
            "not_in_other_tree": sum(1 for e in es if e.get("in_other_tree") is False),
            "text_runs": len(runs), "text_runs_intact": sum(e["intact"] for e in runs),
            "text_runs_identical": sum(bool(e.get("run", {}).get("identical")) for e in runs),
            "text_runs_not_identical": [(e["role"], e["name"][:40], e.get("run", {}).get("reason") or e.get("run", {}).get("mismatch"))
                                        for e in runs if not e.get("run", {}).get("identical")][:12],
            "share_at_expected": round(sum(e["at_expected"] for e in es) / n, 4),
            "mean_displacement_px": round(float(np.mean(disp)), 1) if disp else None,
            "by_role": {k: v for k, v in sorted(by_role.items())}}


def chrome_shares(nodes: dict) -> dict:
    out = {}
    for c in ("A", "AR", "Q", "E"):
        ns = [n for n in nodes.get(c, []) if n["role"] in O.CHROME_ROLES and O.LETTER.search(n["name"] or "")]
        if not ns:
            continue
        out[c] = {"named": len(ns), "arabic": sum(1 for n in ns if O.ARABIC.search(n["name"])),
                  "tagged": sum(1 for n in ns if O.TAGGED in n["name"])}
    if "Q" in nodes and "A" in nodes:
        q = {(tuple(n["path"]), n["role"]): n["name"] for n in nodes["Q"]}
        a = {(tuple(n["path"]), n["role"]): n["name"] for n in nodes["A"]}
        tagged = [k for k, v in q.items() if O.TAGGED in (v or "")]
        covered = [k for k in tagged if k in a and O.ARABIC.search(a[k] or "")]
        untagged_chrome = sorted({v for k, v in q.items() if k[1] in O.LEAF_ROLES and v and O.LETTER.search(v)
                                  and O.TAGGED not in v})
        out["coverage"] = {"tagged_in_Q": len(tagged), "arabic_in_A_of_tagged": len(covered),
                           "share": round(len(covered) / len(tagged), 4) if tagged else None,
                           "untagged_leaf_names_sample": untagged_chrome[:40]}
    return out


def decide(per_task: list[dict], tol: dict) -> dict:
    K = len(per_task)
    admitted = [r for r in per_task if r["admitted"]]

    def share(key):
        vals = [r[key]["pass"] for r in per_task if r.get(key) is not None and "pass" in r[key]]
        return (round(sum(vals) / len(vals), 4) if vals else None), len(vals)

    i2, n2 = share("o6_E_vs_S")
    i5, n5 = share("p7_AD_vs_AR")
    i6, n6 = share("aa_E_vs_E2")
    t1 = [r["o1"]["E-A"]["identical"] for r in per_task if "E-A" in r["o1"]]
    t2 = [r["o1"]["ER-AR"]["identical"] for r in per_task if "ER-AR" in r["o1"]]
    i3 = round((sum(t1) + sum(t2)) / (len(t1) + len(t2)), 4) if t1 or t2 else None
    par = sum(r.get("o4_ltr", {}).get("parents", 0) for r in per_task)
    same = sum(r.get("o4_ltr", {}).get("same_order", 0) for r in per_task)
    i4 = round(same / par, 4) if par else None
    by_app = defaultdict(lambda: Counter())
    for r in per_task:
        for k, v in r.get("plants", {}).items():
            if isinstance(v, bool):
                by_app[r["app"]][k + "_n"] += 1
                by_app[r["app"]][k] += int(v)
    plants_ok = all(c[k] == c[k + "_n"] and c[k + "_n"] > 0
                    for c in by_app.values() for k in ("o3_shift_detected", "o2_reorder_detected", "o5_doc_detected"))
    pd = [r["o5"]["PD"]["verdict"] for r in per_task if "PD" in r.get("o5", {})]
    pd_ok = bool(pd) and all(v.startswith("fail") for v in pd)
    checks = {
        "I1_positive_controls": {"pass": plants_ok and pd_ok, "synthetic_by_app": {k: dict(v) for k, v in by_app.items()},
                                 "in_app_document_plant_verdicts": dict(Counter(pd))},
        "I2_o6_invisibility": {"share": i2, "n": n2, "pass": i2 is not None and i2 >= SHARE},
        "I3_o1_text_structure": {"share": i3, "n": len(t1) + len(t2), "pass": i3 is not None and i3 >= SHARE},
        "I4_o4_order": {"share": i4, "parents": par, "pass": i4 is not None and i4 >= SHARE},
        "I5_p7_one_layout_treatment": {"share": i5, "n": n5, "pass": i5 is not None and i5 >= SHARE},
        "I6_aa_determinism": {"share": i6, "n": n6, "pass": i6 is not None and i6 >= SHARE},
    }
    instrument = all(v["pass"] for v in checks.values())
    reasons = Counter(x.split(" ")[0] for r in per_task for x in r["admission_reasons"])
    return {"K_candidates": K, "admitted": len(admitted), "K_min": K_MIN, "excluded": K - len(admitted),
            "exclusion_reasons": dict(reasons), "instrument_checks": checks, "instrument_pass": instrument,
            "K0": "PASS" if (len(admitted) >= K_MIN and instrument) else "FAIL", "tolerances": tol,
            "admitted_by_split": dict(Counter(r["split"] for r in admitted)),
            "admitted_by_app": dict(Counter(r["app"] for r in admitted))}


# ------------------------------------------------------------------------------------------
# Admission under the registration's own semantics (P0.8b, P0.9), evaluated after the sweep


def decide_checker_invariance(per_task: list[dict], verdicts: list[dict], cells=("A", "ER", "AR", "PL")) -> dict:
    """K0's admission count under registration v3's P0.8b and P0.9 wording: a content leak or a
    saved-file difference excludes a task only if the task's checker reads it. Operationalized
    (choice made after the committed proxy rule's result, disclosed): the task's gold and its
    do-nothing end state, each opened and saved through the task's own postconfig in every cell
    (goldsave.py), get the same checker verdict in every Phase 1 cell and the placebo as in
    en-LTR. Tasks with neither a gold nor a do-nothing result file fall back to the proxy's
    file-identity rule (A4). A1-A3 as before, with A2 comparing titles across cells and with the
    postconfig target only where the en-LTR window carries that target.
    """
    by = {}
    for v in verdicts:
        mid = v.get("mutant_id") or ""
        task, _, rest = mid.partition("__")
        kind, _, cell = rest.partition("__")
        by[(task, kind, cell)] = v
    out = []
    for r in per_task:
        t = r["task_id"]
        reasons = []
        for x in r["admission_reasons"]:
            code = x.split(" ")[0]
            if code in ("A1", "A3"):
                reasons.append(x)
        titles = r.get("titles_by_cell") or {}
        # A2': identical titles across the Phase 1 cells and the placebo
        if not r.get("titles_identical", True):
            reasons.append("A2' titles differ across cells")
        tested = False
        for kind in ("gold", "initial"):
            e = by.get((t, kind, "E"))
            if e is None:
                continue
            tested = True
            for c in cells:
                v = by.get((t, kind, c))
                if v is None:
                    reasons.append(f"A4' no {kind} verdict in {c}")
                elif (v.get("verdict"), v.get("score")) != (e.get("verdict"), e.get("score")):
                    reasons.append(f"A4' {kind} verdict {e.get('verdict')}/{e.get('score')} in E, "
                                   f"{v.get('verdict')}/{v.get('score')} in {c}")
        if not tested:
            reasons += [x for x in r["admission_reasons"] if x.startswith("A4")]
        out.append({"task_id": t, "app": r["app"], "split": r["split"], "admitted": not reasons,
                    "reasons": reasons, "checker_tested": tested,
                    "gold_E": (by.get((t, "gold", "E")) or {}).get("verdict"),
                    "leaks": sorted(r.get("content_leaks", {}))})
    adm = [x for x in out if x["admitted"]]
    return {"admitted": len(adm), "K_min": K_MIN, "tasks": out,
            "admitted_by_app": dict(Counter(x["app"] for x in adm)),
            "admitted_by_split": dict(Counter(x["split"] for x in adm)),
            "reasons": dict(Counter(y.split(" ")[0] + " " + y.split(" ")[1] for x in out for y in x["reasons"])),
            "admitted_task_ids": sorted(x["task_id"] for x in adm)}
