"""Summary of an S2 v4 VM-lane development smoke (dev split only; not Phase 0).

Reads a lane run directory (``probes.jsonl``, ``slots/*/probe.json`` and the post-setup
screenshots kept on the host) and writes ``smoke-summary.json`` with no image in it: per slot the
image check, setup, keyboard map, window titles' match with the postconfig's activation target,
the accessibility summary (Arabic chrome share, menu bar order), the postconfig's saves and the
checker's verdict on the do-nothing state; per task the masked pixel differences between cells
that the registration's instrument checks use (E against S, E against E2, AD against AR) and,
for scale, A against E and ER against E. Masks as the registration's K0 section: the GNOME top bar
(rows 0-31) and each render's caret mask (pixels that differ between its two screenshots).

Runs where Pillow and numpy exist (the checker-mutation metric image). Usage:
  python -m harness.s2_locale.smoke_summary RUN_DIR [--pool pool-v3.json] [--out FILE]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

SHELL_ROWS = 32
EXPECT = {
    "S": {"arabic": False, "order": "ltr"},
    "E": {"arabic": False, "order": "ltr"},
    "A": {"arabic": True, "order": "ltr"},
    "ER": {"arabic": False, "order": "rtl"},
    "AR": {"arabic": True, "order": "rtl"},
    "PL": {"arabic": False, "order": "ltr"},
    "AD": {"arabic": True, "order": "rtl"},
}


def load_image(path: Path):
    import numpy as np
    from PIL import Image

    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


def caret_mask(slot_dir: Path):
    import numpy as np

    a = load_image(slot_dir / "screens" / "post_setup-1.png")
    b = load_image(slot_dir / "screens" / "post_setup-2.png")
    if a.shape != b.shape:
        return np.ones(a.shape[:2], dtype=bool)
    return (a != b).any(axis=2)


def masked_diff(dir_a: Path, dir_b: Path) -> dict[str, Any]:
    import numpy as np

    a = load_image(dir_a / "screens" / "post_setup-1.png")
    b = load_image(dir_b / "screens" / "post_setup-1.png")
    if a.shape != b.shape:
        return {"diff_pixels": None, "reason": f"shapes {a.shape} {b.shape}"}
    mask = caret_mask(dir_a) | caret_mask(dir_b)
    mask[:SHELL_ROWS, :] = True
    diff = (a != b).any(axis=2) & ~mask
    ys, xs = np.nonzero(diff)
    box = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if len(xs) else None
    return {"diff_pixels": int(diff.sum()), "masked_pixels": int(mask.sum()), "bbox": box}


def slot_row(rec: dict[str, Any], strict_titles: list[str]) -> dict[str, Any]:
    post = rec.get("post_setup") or {}
    facts = post.get("facts") or {}
    summary = (post.get("a11y") or {}).get("summary") or {}
    titles = facts.get("window_titles") or []
    files = rec.get("result_files") or {}
    cell = rec.get("cell")
    expect = EXPECT.get(cell, {})
    share = summary.get("arabic_share")
    arabic_ok = None if share is None else (share >= 0.5) == expect.get("arabic")
    return {
        "slot": rec.get("slot"),
        "task": rec.get("task_id", "")[:8],
        "cell": cell,
        "status": rec.get("status"),
        "infrastructure_type": rec.get("infrastructure_type"),
        "image_check_failed": rec.get("infrastructure_type") == "probe:image_check",
        "setup_failures": len((rec.get("setup") or {}).get("failures") or []),
        "stable_two_shots": post.get("stable"),
        "keyboard_layout": facts.get("keyboard_layout"),
        "ar_catalogs": (rec.get("facts_boot") or {}).get("ar_catalogs"),
        "toolbar_digest": ((rec.get("facts_boot") or {}).get("toolbars") or {}).get("sha256"),
        "input_methods": facts.get("input_methods"),
        "input_sources": facts.get("input_sources"),
        "ibus_engine": facts.get("ibus_engine"),
        "server_locale_env": facts.get("server_locale_env"),
        "office_locale_env": [p.get("locale_env")
                              for p in facts.get("libreoffice_processes") or []],
        "p010_values": (rec.get("p010") or {}).get("values"),
        "fc_match_ar": (rec.get("end_facts") or {}).get("fc_match_ar"),
        "arabic_font_families": (rec.get("end_facts") or {}).get("arabic_font_families"),
        "unmet_packages": {k: v.get("status") for k, v in
                           ((rec.get("end_facts") or {}).get("packages") or {}).items()},
        "strict_title_present": all(t in titles for t in strict_titles) if strict_titles else None,
        "arabic_share": share,
        "named_showing": summary.get("named_showing"),
        "menubar_first": summary.get("menubar_first"),
        "menubar_order": summary.get("menubar_order"),
        "arabic_as_expected": arabic_ok,
        "order_as_expected": (summary.get("menubar_order") == expect.get("order")
                              if summary.get("menubar_order") else None),  # fmt: skip
        "postconfig_failures": len((rec.get("postconfig") or {}).get("failures") or []),
        "saves_rewritten": {p: v.get("rewritten") for p, v in files.items()},
        "verdict_donothing": rec.get("verdict"),
        "boot_s": (rec.get("timings") or {}).get("boot_s"),
        "run_s": (rec.get("timings") or {}).get("run_s"),
    }


def summarize(run_dir: Path, pool: dict[str, Any] | None = None) -> dict[str, Any]:
    titles = {}
    if pool:
        for t in pool.get("tasks", []):
            titles[t["task_id"][:8]] = [x for x, s in zip(t.get("activate_window_titles") or [],
                                                          t.get("activate_window_strict") or [],
                                                          strict=False) if s]  # fmt: skip
    latest: dict[str, tuple[int, Path, dict]] = {}
    for probe in sorted((run_dir / "slots").glob("*/probe.json")):
        rec = json.loads(probe.read_text())
        attempt = int(rec.get("attempt") or 1)
        if rec.get("slot") not in latest or attempt > latest[rec["slot"]][0]:
            latest[rec["slot"]] = (attempt, probe.parent, rec)
    rows = [slot_row(rec, titles.get(rec.get("task_id", "")[:8], []))
            for _, _, rec in latest.values()
            if rec.get("kind", "capture") == "capture"]  # fmt: skip
    golds = sorted(({"slot": rec.get("slot"), "task": rec.get("task_id", "")[:8],
                     "cell": rec.get("cell"), "status": rec.get("status"),
                     "infrastructure_type": rec.get("infrastructure_type"),
                     "verdict": rec.get("verdict"), "score": rec.get("score"),
                     "k2_status": (rec.get("k2") or {}).get("status"),
                     "selector_in_guest": rec.get("selector_in_guest")}
                    for _, _, rec in latest.values() if rec.get("kind") == "gold"),
                   key=lambda r: (r["task"], r["cell"] or ""))  # fmt: skip
    by_task: dict[str, dict[str, Path]] = defaultdict(dict)
    for slot, (_, path, rec) in latest.items():
        if rec.get("status") == "probed" and rec.get("kind", "capture") == "capture":
            rep = slot.rsplit(":r", 1)[-1]
            key = rec["cell"] if rep == "1" else f"{rec['cell']}{rep}"
            by_task[rec["task_id"][:8]][key] = path
    pairs = {"E_vs_S": ("E", "S"), "E_vs_E2": ("E", "E2"), "AD_vs_AR": ("AD", "AR"),
             "A_vs_E": ("A", "E"), "ER_vs_E": ("ER", "E"), "PL_vs_E": ("PL", "E")}  # fmt: skip
    diffs: dict[str, dict[str, Any]] = {}
    for task, cells in sorted(by_task.items()):
        diffs[task] = {name: masked_diff(cells[a], cells[b]) for name, (a, b) in pairs.items()
                       if a in cells and b in cells}  # fmt: skip
    verdicts: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in rows:
        verdicts[row["task"]][row["cell"]] = row["verdict_donothing"]
    receipt = run_dir / "lane-receipt.json"
    return {
        "schema": "s2v4-smoke-summary-v1",
        "development_only": True,
        "lane_receipt": json.loads(receipt.read_text()) if receipt.is_file() else None,
        "slots": sorted(rows, key=lambda r: (r["task"], r["cell"] or "", r["slot"])),
        "gold_slots": golds,
        "pixel_diffs": diffs,
        "donothing_verdicts": verdicts,
        "masks": {"shell_rows": SHELL_ROWS, "caret": "pixels differing between the two shots"},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--pool", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    pool = json.loads(args.pool.read_text()) if args.pool else None
    out = summarize(args.run_dir, pool)
    if out.get("lane_receipt"):
        out["lane_receipt"].pop("snapshots", None)
    target = args.out or args.run_dir / "smoke-summary.json"
    target.write_text(json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False))
    print(json.dumps({"slots": len(out["slots"]), "tasks": len(out["pixel_diffs"]),
                      "out": str(target)}))  # fmt: skip
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
