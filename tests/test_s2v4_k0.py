"""S2 v4 K0: the committed admission rule and instrument checks, on synthetic records."""

from __future__ import annotations

import copy

import pytest

from harness.s2_locale import k0_v4 as K


def _task(tid="aaaaaaaa-1", gold="pass", **cell_edits):
    cell = {"observed": True, "setup_failed": False, "titles": ["x.xlsx - LibreOffice Calc"],
            "rewritten": {"/home/user/x.xlsx": True}, "donothing": "fail", "gold": gold}
    cells = {c: copy.deepcopy(cell) for c in K.ADMISSION_CELLS}
    for key, value in cell_edits.items():
        c, field = key.split("__")
        cells[c][field] = value
    return {"task_id": tid, "strict_titles": ["x.xlsx - LibreOffice Calc"], "cells": cells}


def test_admitted_runnable_excluded():
    assert K.admit(_task())["status"] == "admitted"
    assert K.admit(_task(gold=None)) == {"task_id": "aaaaaaaa-1", "status": "runnable",
                                         "reasons": ["no_passing_side_control"]}
    assert K.admit(_task(gold="fail"))["status"] == "runnable"


@pytest.mark.parametrize("edits, reason", [
    ({"AR__observed": False, "AR__setup_failed": True}, "A1:AR:setup_failed"),
    ({"PL__observed": False}, "unobserved:PL"),
    ({"A__titles": ["غير مسمى 1 - LibreOffice Calc"]}, "A2:A"),
    ({"ER__rewritten": {"/home/user/x.xlsx": False}}, "A3:ER:/home/user/x.xlsx"),
    ({"AR__donothing": "pass"}, "A4i:AR"),
    ({"A__gold": "fail"}, "A4ii:A"),
    ({"PL__gold": None}, "unobserved_gold:PL"),
])
def test_exclusions(edits, reason):
    out = K.admit(_task(**edits))
    assert out["status"] == "excluded" and reason in out["reasons"]


def test_title_absent_in_e_is_not_an_exclusion_and_e_not_saved_is_not_required():
    t = _task(E__titles=["Untitled 1 - LibreOffice Calc"], E__rewritten={"/home/user/x.xlsx": False},
              A__titles=[], ER__rewritten={})
    assert K.admit(t)["status"] == "admitted"


def test_c1_tasks_held_until_p010():
    t = _task(tid="0f84bef9-aaaa")
    assert K.admit(t)["reasons"] == ["C1:held"]
    t["p010_pass"] = True
    assert K.admit(t)["status"] == "admitted"


def test_tolerance_formula():
    assert K.tolerance([]) == 50 and K.tolerance([0, 3, 20]) == 50
    assert K.tolerance([31, 7]) == 50 and K.tolerance([5000, 40, 2]) == 80  # one outlier ignored


def _metrics(**edits):
    m = {
        "o5_block_detected": [True] * 100, "pd_detected": {t: True for t in K.PD_VISIBLE_DEV},
        "e_vs_s": [0] * 100, "e_vs_e2": [0] * 99 + [400], "ad_vs_ar": [28] * 100,
        "aa_dev": [0] * 17, "o1_text_pairs": [True] * 200, "o4_parents": [True] * 900,
        "o3_shift_detected": [True] * 95 + [False] * 5, "o2_swap_detected": [True] * 89 + [False] * 11,
    }
    m.update(edits)
    return m


def test_instrument_checks_and_descriptor_validity():
    out = K.instrument_checks(_metrics())
    assert out["pass"] and out["tol6"] == 50
    assert out["I6_e_vs_e2"]["k"] == 99 and out["I6_e_vs_e2"]["pass"]
    assert out["descriptors"]["o3_shift"]["pass"] and not out["descriptors"]["o2_swap"]["pass"]
    assert not out["descriptors"]["valid"]  # a descriptor failure does not fail K0
    assert not K.instrument_checks(_metrics(o5_block_detected=[True] * 99 + [False]))["pass"]
    pd = {t: True for t in K.PD_VISIBLE_DEV}
    pd["af23762e"] = False
    assert not K.instrument_checks(_metrics(pd_detected=pd))["pass"]
    assert not K.instrument_checks(_metrics(e_vs_s=[0] * 94 + [999] * 6))["pass"]
    assert not K.instrument_checks(_metrics(o5_block_detected=[]))["pass"]
    assert not K.instrument_checks(_metrics(ad_vs_ar=[999] * 10 + [0] * 90))["pass"]
    reported = K.instrument_checks(_metrics(o1_text_pairs=[False] * 50 + [True] * 150,
                                            o4_parents=[False] * 100 + [True] * 800))
    assert reported["pass"]  # I3 and I4 are reported, not gating
    assert not reported["I3_o1_text_pairs"]["pass"] and not reported["I4_o4_order"]["pass"]


def test_decide_needs_62_admitted():
    tasks = [_task(tid=f"{i:08x}-x") for i in range(62)] + [_task(tid="ffffffff-y", gold=None)]
    out = K.decide(tasks, _metrics())
    assert out["K0"] == "PASS" and out["admitted"] == 62 and out["runnable"] == 63
    out = K.decide(tasks[1:], _metrics())
    assert out["K0"] == "FAIL" and out["admitted"] == 61


def test_admission_inputs_from_the_dev_smoke_records():
    import json
    from pathlib import Path

    from harness.s2_locale import k0_inputs as I

    root = Path(__file__).resolve().parents[1]
    records = I.load_records([root / "program/evidence/2026-10-11/s2v4-image/smoke-1197/probes.jsonl"])
    pool = json.loads((root / "program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/"
                       "compute/pool/pool-v3.json").read_text())  # fmt: skip
    tasks = I.tasks_from_records(records, I.strict_titles(pool))
    assert len(tasks) == 3 and all(set(t["cells"]) == set(K.ADMISSION_CELLS) for t in tasks)
    e = tasks[0]["cells"]["E"]
    assert e["observed"] and e["titles"] and e["donothing"] == "fail" and all(e["rewritten"].values())
    # smoke 1197 ran no gold slots: every task lacks a passing-side control there
    assert [r["status"] for r in I.admission(records, pool)] == ["runnable"] * 3


def test_admission_inputs_setup_failure_and_gold():
    from harness.s2_locale import k0_inputs as I

    def rec(cell, kind="capture", attempt=1, **kw):
        base = {"task_id": "t-1", "cell": cell, "kind": kind, "attempt": attempt,
                "slot": f"t-1:{cell}:{'g' if kind == 'gold' else 'r'}1"}
        return {**base, **kw}

    ok = {"status": "probed", "verdict": "fail", "post_setup": {"facts": {"window_titles": ["w"]}},
          "result_files": {"/home/user/x": {"rewritten": True}}}
    rows = [rec(c, **ok) for c in K.ADMISSION_CELLS]
    rows += [rec(c, "gold", status="probed", verdict="pass") for c in K.ADMISSION_CELLS]
    assert I.admission(rows, {"tasks": []})[0]["status"] == "admitted"
    rows[1] = rec("A", status="infrastructure", infrastructure_type="probe:reset_task")
    rows.append(rec("A", attempt=2, status="infrastructure", infrastructure_type="probe:reset_task"))
    out = I.admission(rows, {"tasks": []})[0]
    assert out["status"] == "excluded" and "A1:A:setup_failed" in out["reasons"]
