#!/usr/bin/env python3
"""S2 v3 Phase 0 repair pilot, debug job 2: check the interface-language fix (UILocale), the
icon-theme symlink fix, the table pairing of code strings, and three placebo window-state forms.
CPU only, container only."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture as C  # noqa: E402
import catalog as CAT  # noqa: E402


def placebo_selector(form: str) -> str:
    base = C.selector("E").replace(C.XCD_TAIL, "")
    body = ""
    for app in C.PLACEBO_APPS:
        nodes = ""
        for k, tb in enumerate(C.TOOLBAR_STATES.get(app, [])):
            if form == "v1":
                props = C.prop("DockingArea", "1")
            else:
                pos = "0,0" if tb.endswith("standardbar") else "0,1"
                props = (C.prop("DockingArea", "1") + C.prop("Docked", "true") + C.prop("DockPos", pos))
                if form == "v3":
                    props = props.replace(' oor:finalized="true"', "")
            nodes += f'<node oor:name="{tb}" oor:op="fuse">{props}</node>'
        body += C.comp("org.openoffice.Office.UI", app, f'<node oor:name="UIElements"><node oor:name="States">{nodes}</node></node>')
    return base + body + C.XCD_TAIL


def ys(a11y_path: Path, names=("Save", "Bold", "Open")) -> dict:
    d = json.loads(a11y_path.read_text())
    out = {}
    for n in d["nodes"]:
        if n["showing"] and n["role"] == "push button" and n["name"] in names:
            out.setdefault(n["name"], n["box"])
    return out


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    rec: dict = {}
    calc = Path("/etc/libreoffice/registry/calc.xcd").read_text(errors="replace")
    i = calc.find("CalcWindowState")
    j = calc.find('oor:name="private:resource/toolbar/standardbar"', i)
    rec["calc_xcd_standardbar"] = calc[j - 50:j + 900]
    j = calc.find('oor:name="private:resource/toolbar/formatobjectbar"', i)
    rec["calc_xcd_formatobjectbar"] = calc[j - 50:j + 900]
    prof = (C.PROFILE_TEMPLATE / "registrymodifications.xcu").read_text(errors="replace")
    rec["profile_windowstate_items"] = re.findall(r'<item oor:path="[^"]*WindowState[^"]*"[^\n]{0,300}', prof)[:30]
    rec["profile_uilocale"] = re.findall(r'<item oor:path="/org.openoffice.Office.Linguistic/General"><prop oor:name="UILocale"[^\n]{0,200}', prof)
    rec["profile_lines"] = len(prof.splitlines())
    cat_dir = Path("/tmp/cat")
    rec["catalog"] = {k: v for k, v in CAT.build(cat_dir).items() if k != "ui_domains"}
    pairs = (cat_dir / "code-pairs.tsv").read_text().splitlines()
    rec["english_usa_pairs"] = [p for p in pairs if p.endswith("\tEnglish (USA)")][:10]
    C.TOOLBAR_STATES = C.toolbar_states()
    w = C.Worker(0, cat_dir, "yaru")
    rec["worker"] = w.setup()
    pool = json.loads(Path("/src/pool-v3.json").read_text())
    task = next(t for t in pool["tasks"] if t["task_id"].startswith("12382c62"))
    orig = C.selector
    for cell in ("E", "A", "Q", "AR"):
        r = C.render(w, task, cell, out, cat_dir / "code-pairs.tsv", False)
        d = json.loads((out / "a11y" / task["task_id"] / f"{cell}.json").read_text())
        names = [n["name"] for n in d["nodes"] if n["showing"] and n["name"]]
        rec[f"render_{cell}"] = {"saved": r.get("saved"), "save_events": [e for e in r["postconfig"]["events"] if "save" in e],
                                 "n_names": len(names), "arabic": sum(1 for x in names if re.search("[؀-ۿ]", x)),
                                 "tagged": sum(1 for x in names if "‖" in x),
                                 "menus": [n["name"] for n in d["nodes"] if n["showing"] and n["role"] == "menu"][:12],
                                 "buttons": ys(out / "a11y" / task["task_id"] / f"{cell}.json")}
        print(cell, json.dumps(rec[f"render_{cell}"], ensure_ascii=False)[:600], flush=True)
    for form in ("v1", "v2", "v3"):
        C.selector = lambda cell, f=form: placebo_selector(f) if cell == "PL" else orig(cell)
        r = C.render(w, task, "PL", out / form, cat_dir / "code-pairs.tsv", False)
        rec[f"placebo_{form}"] = ys(out / form / "a11y" / task["task_id"] / "PL.json")
        print(form, rec[f"placebo_{form}"], flush=True)
    C.selector = orig
    (out / "debug-record.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    w.stop()
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
