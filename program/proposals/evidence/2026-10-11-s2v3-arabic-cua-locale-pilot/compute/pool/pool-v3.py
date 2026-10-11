#!/usr/bin/env python3
"""S2 v3 Phase 0 (a): the enlarged LibreOffice task pool, frozen before any localized data.

Reads OSWorld's task list at the pinned revision b138d348 (evaluation_examples/test_all.json and
the per-task configs), the checker-mutation study's seeded splits (splits.json: confirm 120,
dev 32, reserve 53, seed 42), S1a's per-episode records (a1.jsonl) and S1a's frozen plan
(plan-a0a.json: S1a-flagged tasks, A0a dev tasks), and writes pool-v3.json.

Rules (registration s2-arabic-cua-locale-v3, P0.1), applied in this order to every OSWorld task
whose domain is libreoffice_calc, libreoffice_impress or libreoffice_writer:
  E1 infeasible (checker `infeasible`): no checker to measure; excluded.
  E2 outside the 205-task file-checker scope of the splits (no split): excluded, reason kept.
  E3 a setup step clicks or moves the pointer at screen coordinates (pyautogui click, moveTo,
     doubleClick): a mirrored layout would send the click to another control, so setup would
     diverge across cells; excluded.
  E4 the checker cannot pass its own raw gold in the checker-mutation controls: 8472fece
     (controls-reserve-v1) and the four K1 raw-gold failures S1a also left out (0a0faba3,
     15aece23, ac1b39ff, ed43c15f; q2-stage1-rescoped-v1 section 6): excluded.
  E5 setup needs the network (pip, apt, snap, extension installs): excluded (none found).
  C1 the checker reads LibreOffice's user configuration (registrymodifications.xcu):
     conditional on the config-invariance probe (P0.10).
  F1 the checker reads a sheet of the result file by the default Calc name of a sheet the agent
     creates ("RNSheet2"; the instruction asks for a new sheet "Sheet2"): flagged; held fixed by pinning
     Office.Calc/Defaults/Sheet/SheetPrefix = "Sheet" in all four cells (P0.5), and verified by
     the functional A/A (P0.9).
Every remaining task is admitted to the Phase 0 candidate pool. Multi-application tasks are out
(a second application has its own interface switch). Split roles: dev tasks are Phase 0's
development set (switch development, oracle tolerances, A/A, positive controls); confirm and
reserve tasks are touched by Phase 0 only through frozen checks. All admitted tasks, dev
included, form the Phase 1 census (no selection on outcomes).

Usage: python3 pool-v3.py <OSWorld dir> <splits.json> <a1.jsonl> <plan-a0a.json> <out.json>
Deterministic; no randomness.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

LO = ("libreoffice_calc", "libreoffice_impress", "libreoffice_writer")
E4_RAW_GOLD_FAILS = {"8472fece", "0a0faba3", "15aece23", "ac1b39ff", "ed43c15f"}
SHEET_DEFAULT_RE = re.compile(r'"RNSheet[2-9]"')
COORD_RE = re.compile(r"pyautogui\.(?:click|doubleClick|moveTo|rightClick|tripleClick|dragTo)")
NET_RE = re.compile(r"pip install|apt(?:-get)? install|snap install|--install-extension|code --install")
CONFIG_FILES = ("registrymodifications.xcu",)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def funcs_of(ev):
    f = ev.get("func")
    return f if isinstance(f, list) else [f]


def result_paths(ev):
    r = ev.get("result")
    rs = r if isinstance(r, list) else [r]
    out = []
    for x in rs:
        if isinstance(x, dict):
            out.append((x.get("type"), x.get("path") or x.get("file_name") or ""))
    return out


def main() -> int:
    osw, splits_p, a1_p, plan_p, out_p = map(Path, sys.argv[1:6])
    test_all_p = osw / "evaluation_examples" / "test_all.json"
    if not test_all_p.exists():
        test_all_p = osw / "test_all.json"
    ex_root = test_all_p.parent / "examples"
    test_all = json.loads(test_all_p.read_text())
    splits = json.loads(splits_p.read_text())
    split_of = {t: k for k in ("confirm", "dev", "reserve") for t in splits[k]}
    plan = json.loads(plan_p.read_text())
    flagged = set(plan["flagged_tasks"])
    dev_a0a = set(plan["dev_tasks_a0a"])
    s1a = defaultdict(list)
    for line in a1_p.open():
        r = json.loads(line)
        if r["size"] == "9B":
            s1a[r["task_id"]].append(r)
    rows = []
    for dom in LO:
        for tid in test_all[dom]:
            p = ex_root / dom / f"{tid}.json"
            t = json.loads(p.read_text())
            ev = t.get("evaluator", {})
            funcs = funcs_of(ev)
            cfg = json.dumps(t.get("config", []))
            evtxt = json.dumps(ev)
            instr = t.get("instruction", "")
            setup_types = [s.get("type") for s in t.get("config", [])]
            rp = result_paths(ev)
            reads_cfg = any(any(c in path for c in CONFIG_FILES) for _, path in rp) or "registrymodifications" in evtxt
            postconfig = ev.get("postconfig", []) or []
            act = [s["parameters"].get("window_name") for s in postconfig if s.get("type") == "activate_window"]
            strict = [bool(s["parameters"].get("strict")) for s in postconfig if s.get("type") == "activate_window"]
            ctrl_s = sum(1 for s in postconfig if re.search(r"hotkey\(\\?[\"']ctrl\\?[\"'],\s*\\?[\"']s\\?[\"']\)", json.dumps(s)))
            reason = None
            if "infeasible" in funcs:
                reason = "E1_infeasible"
            elif tid not in split_of:
                reason = "E2_outside_file_checker_scope"
            elif COORD_RE.search(cfg):
                reason = "E3_coordinate_setup"
            elif tid[:8] in E4_RAW_GOLD_FAILS:
                reason = "E4_checker_fails_raw_gold"
            elif NET_RE.search(cfg):
                reason = "E5_network_setup"
            cls = "excluded" if reason else ("conditional_config_checker" if reads_cfg else "strict")
            sheet_flag = bool(SHEET_DEFAULT_RE.search(evtxt))
            rs = s1a.get(tid, [])
            k_h = {h: sum(1 for r in rs if r["harness"] == h and r["score"] == 1.0) for h in ("H-OSW-fixed", "H-GA")}
            n_h = {h: sum(1 for r in rs if r["harness"] == h) for h in ("H-OSW-fixed", "H-GA")}
            rows.append({
                "task_id": tid, "app": dom, "split": split_of.get(tid, "none"), "class": cls, "exclusion": reason,
                "task_config_sha256": sha(p), "checker_funcs": funcs, "result_inputs": rp,
                "setup_step_types": setup_types, "activate_window_titles": act, "activate_window_strict": strict,
                "postconfig_ctrl_s_steps": ctrl_s, "f1_default_sheet_name": sheet_flag,
                "s1a_flagged": tid in flagged, "s1a_a0a_dev": tid in dev_a0a,
                "s1a_9b_k": sum(k_h.values()) if rs else None, "s1a_9b_n": sum(n_h.values()) if rs else None,
                "s1a_9b_k_by_harness": k_h if rs else None, "s1a_9b_n_by_harness": n_h if rs else None,
                "s1a_9b_slot_mean_s": (sum(r["host"]["slot_occupancy_s"] for r in rs) / len(rs)) if rs else None,
                "instruction_head": instr[:120],
            })
    adm = [r for r in rows if r["class"] != "excluded"]
    summary = {
        "lo_tasks_in_test_all": len(rows),
        "by_app": dict(Counter(r["app"] for r in rows)),
        "excluded": dict(Counter(r["exclusion"] for r in rows if r["exclusion"])),
        "excluded_ids": {r["task_id"][:8]: r["exclusion"] for r in rows if r["exclusion"]},
        "admitted": len(adm),
        "admitted_by_split": dict(Counter(r["split"] for r in adm)),
        "admitted_by_app": dict(Counter(r["app"] for r in adm)),
        "admitted_by_split_app": {f"{s}/{a}": n for (s, a), n in sorted(Counter((r["split"], r["app"]) for r in adm).items())},
        "conditional_config_checker": [r["task_id"][:8] for r in adm if r["class"] == "conditional_config_checker"],
        "f1_default_sheet_name": {r["task_id"][:8]: r["split"] for r in adm if r["f1_default_sheet_name"]},
        "with_s1a_9b_records": sum(1 for r in adm if r["s1a_9b_n"]),
        "s1a_informative_ge1_of_8": sum(1 for r in adm if (r["s1a_9b_k"] or 0) >= 1),
        "s1a_never_solved": sum(1 for r in adm if r["s1a_9b_n"] and r["s1a_9b_k"] == 0),
        "s1a_mean_success_on_overlap": (sum(r["s1a_9b_k"] for r in adm if r["s1a_9b_n"]) /
                                        max(1, sum(r["s1a_9b_n"] for r in adm if r["s1a_9b_n"]))),
        "without_s1a_records": sum(1 for r in adm if not r["s1a_9b_n"]),
        "s1a_flagged_admitted": [r["task_id"][:8] for r in adm if r["s1a_flagged"]],
        "checker_funcs_admitted": dict(Counter(f for r in adm for f in r["checker_funcs"]).most_common()),
        "activate_window_strict_tasks": sum(1 for r in adm if any(r["activate_window_strict"])),
        "postconfig_ctrl_s_tasks": sum(1 for r in adm if r["postconfig_ctrl_s_steps"]),
    }
    out = {
        "schema": "s2v3-pool-v1",
        "inputs": {"test_all_json_sha256": sha(test_all_p), "osworld_revision": "b138d348256078fa634fc3b73567a7337c793e6b",
                   "splits_json_sha256": sha(splits_p), "a1_jsonl_sha256": sha(a1_p), "plan_a0a_sha256": sha(plan_p)},
        "rules": __doc__.split("Rules")[1].split("Usage:")[0].strip(),
        "summary": summary,
        "tasks": rows,
    }
    out_p.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
