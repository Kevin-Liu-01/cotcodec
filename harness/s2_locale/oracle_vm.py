"""S2 v4 Phase 0: the render oracle on the VM lane's renders, and K0's instrument metrics.

Registration ``s2-arabic-cua-locale-v4`` P0.7 and section "K0": the S2 v3 oracle
(``oracle.py``, ``phase0.py``'s plants) adapted to what the VM lane records per capture slot
(``vm_probe.py``): two post-setup screenshots 1 s apart and OSWorld's accessibility tree (the
guest server's XML; ``xml_nodes`` turns it into the oracle's node list). It reads lane run
directories (screenshots and trees stay on the host), never the agent, and returns per task the
quantities K0 reads and the oracle's descriptors, and the global instrument metrics in the shape
``k0_v4.instrument_checks`` takes.

Definitions (fixed before the freeze; every parameter from the 17 dev tasks by a formula):

* Renders. A (task, cell, rep) render is the capture slot's counted attempt (``k0_inputs.counted``:
  the first job with a final record, its last attempt) when it ended ``probed``; E2 and ER2 are the
  rep-2 capture slots of E and ER; PD is the PD slot (the ER image with the planted document).
* Masks (K0): the GNOME top bar (rows 0-31) and, per render, the caret mask (every pixel that
  differs between its two screenshots), applied to both renders compared.
* Pixel count. A pixel differs when any channel differs by more than ``oracle.INK_DIFF / 2`` (the
  v3 oracle's ``pixel_diff`` threshold); counted outside the masks on the first screenshots.
  The exact count (any change) is reported beside it.
* tol5 = tol6 = ``k0_v4.tolerance`` of the dev tasks' masked E-vs-E2 counts; tol2 and tol3 by
  v3.1's formulas (``calibrate``) on the dev tasks' renders. The accessibility offset is 0
  (``A11Y_DY``): in the VM's GNOME session AT-SPI reports LibreOffice's VCL widgets at their screen
  position (on the dev renders the spreadsheet's box sits on the grid at offset 0). v3.1's
  ``estimate_dy``, made for the container's window manager, is reported, not used: on the dev
  renders it picks 24-27 px, which moves the document box onto the sheet-tab and scroll bars and
  makes O5 flag A's unchanged grid.
* O5 (``o5``): v3's ``oracle.o5`` with K0's masks (a pixel under either render's caret mask at
  the chosen offset is not counted).
* I1-doc (the operationalization of K0's "O5 detects"; the reference is the unplanted render of
  the same image, so the check isolates the plant from the layout treatment: in the VM, O5 of E
  against ER flags the Calc and Writer dev tasks because the mirrored layout changes which part of
  the document region is visible). Synthetic: on every task with an ER render, an inverted
  48 x 14 block (``phase0.plant_doc``) planted in ER's document region (its own accessibility box;
  E's when ER has none) at a third of its width and height; detected when O5 of ER against the
  planted ER is ``fail_changed`` or ``fail_mirrored`` (so the plant exceeds tol5 through O5's
  alignment and mask). A task with an ER render and no document region counts as not detected.
  In-application: O5 of ER against PD (the same image with the planted document) flags it. O5
  against E is reported beside both.
* I2 (E-S), I5 (AD-AR), I6 (E-E2): the masked counts. I3: O1 text pairs (E-A, ER-AR) identical;
  I4: O4 sibling order E-A per compared parent. Descriptors: the O3 shifted-widget and O2
  halves-swapped plants on ER (``phase0.plant_shift``, ``plant_reorder``), each task's element
  drawn with its own PCG64 generator seeded by (42, the task id's first 32 bits), so the draw does
  not depend on the order or the parallelism of the run.

Runs where numpy, scipy and Pillow exist (the development Mac, or a CPU container job):
  python -m harness.s2_locale.oracle_vm --runs RUN_DIR [RUN_DIR] --pool POOL --out oracle.json
      [--k0 k0.json]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "s2v4-oracle-vm-v1"
SHELL_ROWS = 32
CP = "https://accessibility.ubuntu.example.org/ns/component"
ST = "https://accessibility.ubuntu.example.org/ns/state"
COORD = re.compile(r"\((-?\d+),\s*(-?\d+)\)")
# The v3 dump's walk did not descend into these (whole tables and documents are one element).
NO_DESCEND = ("table", "tree table", "document text", "document spreadsheet",
              "document presentation", "document frame", "paragraph")  # fmt: skip
PLANT_SEED = 42
A11Y_DY = 0  # the VM reports VCL widgets at screen position (dev renders); see the docstring


# --------------------------------------------------------------------------- inputs


def _pair(value: str | None) -> tuple[int, int] | None:
    m = COORD.match(value or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def xml_nodes(xml_text: str) -> list[dict[str, Any]]:
    """OSWorld's accessibility XML as the v3 oracle's nodes: LibreOffice's application subtree,
    each element with a screen box, as ``{path, role, name, box, showing}``; ``path`` is the
    child-index path from the desktop (application index first), ``role`` the AT-SPI role name
    (the XML tag with hyphens as spaces); the walk does not descend into ``NO_DESCEND`` roles."""
    root = ET.fromstring(xml_text)
    out: list[dict[str, Any]] = []

    def walk(el: ET.Element, path: list[int]) -> None:
        role = el.tag.replace("-", " ")
        xy, size = _pair(el.get(f"{{{CP}}}screencoord")), _pair(el.get(f"{{{CP}}}size"))
        if xy is not None and size is not None:
            out.append({"path": path, "role": role, "name": el.get("name") or "",
                        "box": [xy[0], xy[1], size[0], size[1]],
                        "showing": el.get(f"{{{ST}}}showing") == "true"})  # fmt: skip
        if role in NO_DESCEND:
            return
        for i, child in enumerate(el):
            walk(child, [*path, i])

    for i, app in enumerate(root):
        name = app.get("name", "")
        if app.tag == "application" and re.search(r"soffice|libreoffice", name, re.I):
            walk(app, [i])
    return out


def slot_dir(run_dir: Path, slot: str, attempt: int) -> Path:
    return run_dir / "slots" / f"{slot.replace(':', '_')}.a{attempt}"


def render_index(run_dirs: Sequence[Path]) -> dict[tuple[str, str, int], Path]:
    """(task id, cell, rep) -> the slot directory of the counted, probed capture attempt."""
    from harness.s2_locale import k0_inputs

    records = k0_inputs.load_records([d / "probes.jsonl" for d in run_dirs])
    out = {}
    for _sid, rows in k0_inputs.counted(records).items():
        last = rows[-1]
        if last.get("kind", "capture") != "capture" or last.get("status") != "probed":
            continue
        rep = int(str(last["slot"]).rsplit(":r", 1)[1])
        out[(last["task_id"], last["cell"], rep)] = slot_dir(
            run_dirs[int(last.get("_run", 0))], str(last["slot"]), int(last.get("attempt") or 1))
    return out


class Render:
    """One capture slot's two screenshots and accessibility tree (loaded on demand)."""

    def __init__(self, directory: Path):
        self.dir = directory
        self._shots: list[Any] | None = None
        self._nodes: list[dict[str, Any]] | None = None

    @property
    def shots(self) -> list[Any]:
        if self._shots is None:
            from harness.s2_locale import oracle as O

            self._shots = [O.load_png(self.dir / "screens" / f"post_setup-{i}.png")
                           for i in (1, 2)]  # fmt: skip
        return self._shots

    @property
    def img(self) -> Any:
        return self.shots[0]

    @property
    def nodes(self) -> list[dict[str, Any]]:
        if self._nodes is None:
            path = self.dir / "a11y" / "post_setup.xml"
            self._nodes = xml_nodes(path.read_text(encoding="utf-8")) if path.is_file() else []
        return self._nodes

    def caret(self) -> Any:
        a, b = self.shots
        if a.shape != b.shape:
            import numpy as np

            return np.ones(a.shape[:2], dtype=bool)
        return (a != b).any(axis=2)


# --------------------------------------------------------------------------- comparisons


def masked_counts(a: Render, b: Render) -> dict[str, Any]:
    """K0's masked differing-pixel count between two renders' first screenshots."""
    from harness.s2_locale import oracle as O

    x, y = a.img, b.img
    if x.shape != y.shape:
        return {"diff_pixels": None, "reason": f"shapes {x.shape} {y.shape}"}
    mask = a.caret() | b.caret()
    mask[:SHELL_ROWS, :] = True
    thresholded = (abs(x - y).max(axis=2) > O.INK_DIFF // 2) & ~mask
    exact = (x != y).any(axis=2) & ~mask
    return {"diff_pixels": int(thresholded.sum()), "exact_diff_pixels": int(exact.sum()),
            "masked_pixels": int(mask.sum())}  # fmt: skip


def _dev_dy(paths: Mapping[str, Path]) -> int | None:
    from harness.s2_locale import oracle as O

    e = Render(paths["E"]) if "E" in paths else None
    if e is None or not e.nodes:
        return None
    return O.estimate_dy(e.img, O.showing_nodes({"nodes": e.nodes}))


def _dev_parts(job: tuple[Mapping[str, Path], int]) -> dict[str, list[Any]]:
    """One dev task's calibration inputs (``phase0._calib_task`` on the VM renders)."""
    from harness.s2_locale import oracle as O

    paths, dy = job
    r = {c: Render(p) for c, p in paths.items()}
    out: dict[str, list[Any]] = {"elem": [], "trans": [], "dxs": [], "aa": []}
    e, e2 = r.get("E"), r.get("E2")
    if e is None:
        return out
    if e2 is not None:
        count = masked_counts(e, e2)["diff_pixels"]
        if count is not None:
            out["aa"].append(count)
    if not e.nodes:
        return out
    nodes = O.place_nodes(e.img, O.showing_nodes({"nodes": e.nodes}), dy)
    fr = O.frame_box(nodes) or (0, 0, 1920, 1080)
    if e2 is not None:
        out["elem"] = [x["local_mismatch"] for x in O.element_pass(e.img, e2.img, nodes, fr,
                                                                   "identity", 1.0)]  # fmt: skip
    if "PL" in r:
        for x in O.element_pass(e.img, r["PL"].img, nodes, fr, "identity", 0.25):
            if (x["role"] in ("push button", "toggle button") and not x.get("unmoved")
                    and x.get("found_y") is not None
                    and abs(x["found_y"] - x["ink_box"][1]) <= 2
                    and x["found_mismatch"] <= 0.25):  # fmt: skip
                out["trans"].append(x["found_mismatch"])
    if "ER" in r:
        for x in O.element_pass(e.img, r["ER"].img, nodes, fr, "reflect", 0.25, tol3=24):
            if x["near_expected"] and x["local_mismatch"] <= 0.25:
                out["dxs"].append(abs(x["dx"]))
    return out


def calibrate(index: Mapping[tuple[str, str, int], Path], dev: Sequence[str],
              pool: Any = None) -> dict:  # fmt: skip
    """v3.1's dev-task formulas on the VM renders: ``dy`` (the mode of ``estimate_dy`` over the
    dev E renders), tol2 and tol3 (``phase0.calibrate``'s element formulas), and tol5 = tol6 from
    K0's formula on the dev tasks' masked E-vs-E2 counts. ``pool`` (optional) maps the per-task
    work in parallel; the result does not depend on it."""
    import numpy as np

    from harness.s2_locale import k0_v4

    mapper = pool.map if pool is not None else map
    paths = [labelled_paths(index, t) for t in dev]
    dys = [d for d in mapper(_dev_dy, paths) if d is not None]
    dy = A11Y_DY  # v3.1's estimate (the mode of dys) is reported, not used
    parts = list(mapper(_dev_parts, [(p, dy) for p in paths]))
    elem = [x for p in parts for x in p["elem"]]
    trans = [x for p in parts for x in p["trans"]]
    dxs = [x for p in parts for x in p["dxs"]]
    aa = [x for p in parts for x in p["aa"]]
    worst = max(elem) if elem else 0.0
    p95t = float(np.percentile(trans, 95)) if trans else 0.0
    tol6 = k0_v4.tolerance(aa)
    return {"dy_vcl": dy, "dy_estimate_v31": int(Counter(dys).most_common(1)[0][0]) if dys
            else None, "dy_by_dev_task": dys, "aa_dev": aa,
            "aa_elements": len(elem), "aa_worst_element_mismatch": round(worst, 4),
            "translation_elements": len(trans), "translation_p95_mismatch": round(p95t, 4),
            "tol2": round(min(0.10, max(0.02, 2 * worst, p95t)), 4),
            "reflection_dx_elements": len(dxs),
            "tol3": int(max(2, math.ceil(float(np.percentile(dxs, 95))))) if dxs else 2,
            "tol5": tol6, "tol6": tol6}  # fmt: skip


def o5(ref_img: Any, ref_mask: Any, img: Any, img_mask: Any, box: Sequence[int], tol5: int,
       max_dy: int = 60) -> dict[str, Any]:  # fmt: skip
    """v3's O5 (``oracle.o5``: the reference's document region aligned by translation in the other
    render, unflipped and flipped) with K0's masks: at the chosen offset, a pixel under either
    render's caret mask is not counted (the GNOME top bar lies outside every document region)."""
    import numpy as np

    from harness.s2_locale import oracle as O

    def side(flip: bool) -> dict[str, Any]:
        al = O.align_count(ref_img, img, box, max_dy=max_dy, flip=flip)
        if not al.get("ok"):
            return al
        x, y, w, h = box
        xx, yy = x + al["dx"], y + al["dy"]
        crop, cm = ref_img[y:y + h, x:x + w], ref_mask[y:y + h, x:x + w]
        if flip:
            crop, cm = crop[:, ::-1], cm[:, ::-1]
        win, wm = img[yy:yy + h, xx:xx + w], img_mask[yy:yy + h, xx:xx + w]
        diff = (np.abs(win - crop).max(axis=2) > O.INK_DIFF // 2) & ~cm & ~wm
        return {**al, "diff_pixels_unmasked": al["diff_pixels"], "diff_pixels": int(diff.sum())}

    un, fl = side(False), side(True)
    rec: dict[str, Any] = {"unflipped": un, "flipped": fl}
    if not un.get("ok"):
        rec["verdict"] = "no_alignment"
        return rec
    u = un["diff_pixels"]
    f = fl["diff_pixels"] if fl.get("ok") else 10 ** 9
    if u <= tol5 and f <= tol5:
        rec["verdict"] = "uninformative_symmetric"
    elif u <= tol5:
        rec["verdict"] = "pass"
    elif f <= tol5:
        rec["verdict"] = "fail_mirrored"
    else:
        rec["verdict"] = "fail_changed"
    return rec


def detected(verdict: str | None) -> bool:
    """O5 flags a change: neither ``pass`` nor ``uninformative_symmetric`` (nor no verdict)."""
    return verdict in ("fail_changed", "fail_mirrored")


def analyse_task(task: str, r: Mapping[str, Render], tol: Mapping[str, Any], rng: Any) -> dict:
    """One task's oracle record from its renders ``r`` (cell label -> Render; E2, ER2 for reps)."""
    from harness.s2_locale import oracle as O
    from harness.s2_locale import phase0 as P0

    out: dict[str, Any] = {"task_id": task, "cells": sorted(r)}
    for key, (a, b) in {"E_vs_S": ("E", "S"), "E_vs_E2": ("E", "E2"), "AD_vs_AR": ("AD", "AR"),
                        "ER_vs_ER2": ("ER", "ER2"), "A_vs_E": ("A", "E"),
                        "PL_vs_E": ("PL", "E")}.items():  # fmt: skip
        if a in r and b in r:
            out[key] = masked_counts(r[a], r[b])
    nodes = {c: O.showing_nodes({"nodes": x.nodes}) for c, x in r.items()}
    # O1 structure (I3) and O4 order (I4)
    out["o1"] = {f"{a}-{b}": O.structure_diff(nodes[a], nodes[b])
                 for a, b in (("E", "A"), ("ER", "AR"), ("E", "ER"), ("A", "AR"))
                 if nodes.get(a) and nodes.get(b)}  # fmt: skip
    if nodes.get("E") and nodes.get("A"):
        def bx(ns):
            return {tuple(n["path"]): n["box"][0] for n in O.leaf_elements(ns)}

        oa, ob = O.sibling_order(bx(nodes["E"])), O.sibling_order(bx(nodes["A"]))
        out["o4_parents"] = [[x for x in oa[p] if x in set(ob[p])] == [x for x in ob[p]
                                                                         if x in set(oa[p])]
                             for p in sorted(set(oa) & set(ob))]  # fmt: skip
    # O5 and the document plants (I1-doc)
    e = r.get("E")
    placed = O.place_nodes(e.img, nodes["E"], tol["dy_vcl"]) if e is not None and nodes.get("E") \
        else []
    box = O.doc_region(placed) if placed else None
    out["doc_box"] = box
    o5s = {}
    if box is not None:
        for c in ("A", "ER", "AR", "PL", "E2", "PD"):
            if c in r:
                o5s[c] = o5(e.img, e.caret(), r[c].img, r[c].caret(), box, tol["tol5"],
                            max_dy=260 if c == "PL" else 60)  # fmt: skip
    out["o5"] = {c: v.get("verdict") for c, v in o5s.items()}
    out["o5_diff_pixels"] = {c: (v.get("unflipped") or {}).get("diff_pixels")
                             for c, v in o5s.items()}  # fmt: skip
    if "ER" in r:
        er = r["ER"]
        er_box = O.doc_region(O.place_nodes(er.img, nodes["ER"], tol["dy_vcl"])) \
            if nodes.get("ER") else None
        er_box = er_box or box
        out["er_doc_box"] = er_box
        hit = False
        if er_box is not None:
            planted = P0.plant_doc(er.img, er_box)
            verdict = o5(er.img, er.caret(), planted, er.caret(), er_box,
                         tol["tol5"]).get("verdict")  # fmt: skip
            out["o5_block_vs_ER"] = verdict
            hit = detected(verdict)
            if box is not None:  # reported: the plant seen against E (v3's reference)
                out["o5_block_vs_E"] = o5(e.img, e.caret(), planted, er.caret(), box,
                                          tol["tol5"]).get("verdict")  # fmt: skip
        out["o5_block_detected"] = hit
        if "PD" in r:
            pd = r["PD"]
            pd_rec = (o5(er.img, er.caret(), pd.img, pd.caret(), er_box, tol["tol5"])
                      if er_box is not None else {})  # fmt: skip
            out["o5_PD_vs_ER"] = pd_rec.get("verdict")
            out["o5_PD_vs_ER_pixels"] = (pd_rec.get("unflipped") or {}).get("diff_pixels")
            out["pd_detected"] = detected(pd_rec.get("verdict"))
            if box is not None:
                out["o5_PD_vs_E"] = o5(e.img, e.caret(), pd.img, pd.caret(), box,
                                       tol["tol5"]).get("verdict")  # fmt: skip
    elif "PD" in r:
        out["pd_detected"] = False  # no unplanted twin to compare with
    # descriptors: the O3 shifted-widget and O2 halves-swapped plants on ER
    if e is not None and "ER" in r and placed:
        fr = O.frame_box(placed) or (0, 0, 1920, 1080)
        paths = {(tuple(n["path"]), n["role"]) for n in nodes.get("ER", [])}
        elems = O.element_pass(e.img, r["ER"].img, placed, fr, "reflect", tol["tol2"], paths,
                               tol3=tol["tol3"])  # fmt: skip
        out["mirror_elements"] = P0.summarize_elements(elems)
        cand = [x for x in elems if x["at_expected"] and x["ink_box"][2] >= 16]
        if cand:
            el = cand[int(rng.integers(len(cand)))]
            node = next(n for n in placed if n["path"] == el["path"] and n["role"] == el["role"])
            shifted = P0.plant_shift(r["ER"].img, el, dx=tol["tol3"] + 8)
            r1 = O.element_pass(e.img, shifted, [node], fr, "reflect", tol["tol2"],
                                tol3=tol["tol3"])  # fmt: skip
            out["o3_shift_detected"] = bool(r1) and not r1[0]["at_expected"]
            runs = [x for x in cand if x["text_run"] and (x.get("run") or {}).get("identical")]
            if runs:
                elr = runs[int(rng.integers(len(runs)))]
                noder = next(n for n in placed
                             if n["path"] == elr["path"] and n["role"] == elr["role"])
                r2 = O.element_pass(e.img, P0.plant_reorder(r["ER"].img, elr), [noder], fr,
                                    "reflect", tol["tol2"], tol3=tol["tol3"])  # fmt: skip
                out["o2_swap_detected"] = bool(r2) and not (r2[0].get("run") or {}).get(
                    "identical", False)  # fmt: skip
    return out


def labelled_paths(index: Mapping[tuple[str, str, int], Path], task: str) -> dict[str, Path]:
    """A task's renders by label (``E``, ``E2``, ``ER2``, ``PD``, ...)."""
    return {(cell if rep == 1 else f"{cell}{rep}"): path
            for (t, cell, rep), path in index.items() if t == task}


def task_rng(task_id: str) -> Any:
    import numpy as np

    seq = np.random.SeedSequence([PLANT_SEED, int(task_id[:8], 16)])
    return np.random.Generator(np.random.PCG64(seq))


def _analyse(job: tuple[str, Mapping[str, Path], Mapping[str, Any]]) -> dict[str, Any]:
    task, paths, tol = job
    return analyse_task(task, {c: Render(p) for c, p in paths.items()}, tol, task_rng(task))


def metrics(per_task: Sequence[Mapping[str, Any]], tol: Mapping[str, Any]) -> dict[str, Any]:
    """The inputs of ``k0_v4.instrument_checks``."""
    def counts(key: str) -> list[int]:
        return [r[key]["diff_pixels"] for r in per_task
                if key in r and r[key].get("diff_pixels") is not None]

    return {
        "o5_block_detected": [r["o5_block_detected"] for r in per_task if "o5_block_detected" in r],
        "pd_detected": {r["task_id"][:8]: r["pd_detected"] for r in per_task if "pd_detected" in r},
        "e_vs_s": counts("E_vs_S"), "e_vs_e2": counts("E_vs_E2"), "ad_vs_ar": counts("AD_vs_AR"),
        "aa_dev": list(tol["aa_dev"]),
        "o1_text_pairs": [r["o1"][k]["identical"] for r in per_task for k in ("E-A", "ER-AR")
                          if k in r.get("o1", {})],
        "o4_parents": [x for r in per_task for x in r.get("o4_parents", [])],
        "o3_shift_detected": [r["o3_shift_detected"] for r in per_task if "o3_shift_detected" in r],
        "o2_swap_detected": [r["o2_swap_detected"] for r in per_task if "o2_swap_detected" in r],
    }  # fmt: skip


def run(run_dirs: Sequence[Path], pool: Mapping[str, Any], workers: int = 1) -> dict[str, Any]:
    from concurrent.futures import ProcessPoolExecutor

    from harness.s2_locale import k0_v4
    from harness.s2_locale.golds import pool_tasks

    index = render_index(run_dirs)
    tasks = sorted({t for t, _, _ in index})
    dev = [t["task_id"] for t in pool_tasks(pool) if t["split"] == "dev" and t["task_id"] in tasks]
    executor = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None
    try:
        tol = calibrate(index, dev, executor)
        jobs = [(t, labelled_paths(index, t), tol) for t in tasks]
        per_task = list((executor.map if executor else map)(_analyse, jobs))
    finally:
        if executor is not None:
            executor.shutdown()
    m = metrics(per_task, tol)
    return {"schema": SCHEMA, "runs": [str(d) for d in run_dirs], "tasks": len(tasks),
            "dev_tasks": dev, "tolerances": tol, "metrics": m,
            "instrument_checks": k0_v4.instrument_checks(m), "per_task": per_task}  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--k0", type=Path, default=None, help="also write k0_v4.decide's output")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    pool = json.loads(args.pool.read_text(encoding="utf-8"))
    result = run(args.runs, pool, args.workers)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True, default=str))
    if args.k0:
        from harness.s2_locale import k0_inputs, k0_v4

        records = k0_inputs.load_records([d / "probes.jsonl" for d in args.runs])
        tasks = k0_inputs.tasks_from_records(
            records, k0_inputs.strict_titles(pool),
            pool_ids=[t["task_id"] for t in pool["tasks"] if t.get("exclusion") is None])
        args.k0.write_text(json.dumps(k0_v4.decide(tasks, result["metrics"]), indent=1,
                                      sort_keys=True))  # fmt: skip
    print(json.dumps({"tasks": result["tasks"], "tolerances": {
        k: result["tolerances"][k] for k in ("dy_vcl", "tol2", "tol3", "tol6")},
        "instrument_checks_pass": result["instrument_checks"]["pass"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
