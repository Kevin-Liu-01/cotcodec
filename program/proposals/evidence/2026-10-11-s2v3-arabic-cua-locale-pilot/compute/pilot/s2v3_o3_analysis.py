#!/usr/bin/env python3
"""O3 (mirror fidelity) on real LibreOffice widget boxes from pilot job 1100's AT-SPI dumps.

For each task: elements present and showing in both the en-LTR (L1) and en-RTL (L2) dumps are
matched by (tree path, role, name with U+2066-U+2069 stripped). An element is "reflected" if its L2
box is the horizontal reflection of its L1 box inside the LibreOffice window (x' = X + W - (x - X) - w,
same y, within 2 px), and "unmoved" if it keeps its L1 position. Elements inside document content
are excluded by role (the dump does not descend into tables, document frames and paragraphs).
Zero-size and full-window-width elements (whose reflection is the identity) are reported separately.
Usage: python3 s2v3_o3_analysis.py <run-b2 dir> <out.json>
"""
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ISO = "⁦⁧⁨⁩"
TOL = 2


def key(n):
    return (tuple(n["path"]), n["role"], "".join(c for c in n["name"] if c not in ISO))


def main():
    run = Path(sys.argv[1])
    rec = json.loads((run / "pilot-b-record.json").read_text())
    by = {}
    for r in rec["results"]:
        by.setdefault(r["task_id"], {})[r["cell"]] = r
    rows = []
    role_bad = Counter()
    role_all = Counter()
    for tid, cells in sorted(by.items()):
        fa, fb = run / "a11y" / f"{tid}-L1.json", run / "a11y" / f"{tid}-L2.json"
        if not (fa.exists() and fb.exists()):
            continue
        win = next((w for w in cells["L1"].get("windows", []) if "LibreOffice" in w["title"]), None)
        win2 = next((w for w in cells["L2"].get("windows", []) if "LibreOffice" in w["title"]), None)
        if not win or not win2:
            rows.append({"task_id": tid, "app": cells["L1"].get("app"), "no_window": True})
            continue
        X, W = win["x"], win["w"]
        A = {key(n): n for n in json.loads(fa.read_text())["nodes"] if n.get("showing") and n["box"][2] > 0 and n["box"][3] > 0}
        B = {key(n): n for n in json.loads(fb.read_text())["nodes"] if n.get("showing") and n["box"][2] > 0 and n["box"][3] > 0}
        common = sorted(set(A) & set(B))
        refl = same = sym = 0
        bad_examples = []
        for k in common:
            lx, ly, lw, lh = A[k]["box"]
            rx, ry, rw, rh = B[k]["box"]
            exp = X + W - (lx - X) - lw
            symmetric = abs(exp - lx) <= TOL
            role_all[k[1]] += 1
            if symmetric:
                sym += 1
            if abs(rx - exp) <= TOL and abs(ry - ly) <= TOL and abs(rw - lw) <= TOL:
                refl += 1
            else:
                role_bad[k[1]] += 1
                if len(bad_examples) < 5:
                    bad_examples.append({"role": k[1], "name": k[2][:40], "ltr": A[k]["box"], "rtl": B[k]["box"], "expected_x": exp})
            if abs(rx - lx) <= TOL and abs(ry - ly) <= TOL:
                same += 1
        n = len(common)
        rows.append({"task_id": tid, "app": cells["L1"].get("app"), "window": [X, win["y"], W, win["h"]],
                     "window_same_in_rtl": [win2["x"], win2["w"]] == [X, W],
                     "l1_nodes": len(A), "l2_nodes": len(B), "matched": n,
                     "reflected": refl, "reflected_share": refl / n if n else None,
                     "symmetric_matched": sym,
                     "reflected_share_asymmetric": ((refl - sum(1 for k in common if abs((X + W - (A[k]['box'][0] - X) - A[k]['box'][2]) - A[k]['box'][0]) <= TOL and abs(B[k]['box'][0] - A[k]['box'][0]) <= TOL)) / max(1, n - sym)) if n else None,
                     "unmoved_share": same / n if n else None, "not_reflected_examples": bad_examples,
                     "l1_only": len(set(A) - set(B)), "l2_only": len(set(B) - set(A))})
    ok = [r for r in rows if r.get("matched")]
    summary = {
        "tasks_with_both_dumps": len(rows),
        "tasks_matched": len(ok),
        "matched_elements_median": statistics.median(r["matched"] for r in ok) if ok else None,
        "reflected_share_median": statistics.median(r["reflected_share"] for r in ok) if ok else None,
        "reflected_share_p10": sorted(r["reflected_share"] for r in ok)[len(ok) // 10] if ok else None,
        "reflected_share_min": min(r["reflected_share"] for r in ok) if ok else None,
        "reflected_share_asymmetric_median": statistics.median(r["reflected_share_asymmetric"] for r in ok) if ok else None,
        "unmoved_share_median": statistics.median(r["unmoved_share"] for r in ok) if ok else None,
        "by_app_reflected_median": {a: statistics.median(r["reflected_share"] for r in ok if r["app"] == a)
                                    for a in sorted({r["app"] for r in ok})},
        "not_reflected_by_role_top": dict(role_bad.most_common(12)),
        "matched_by_role_top": dict(role_all.most_common(12)),
    }
    Path(sys.argv[2]).write_text(json.dumps({"schema": "s2v3-o3-v1", "tolerance_px": TOL, "summary": summary, "tasks": rows},
                                            indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
