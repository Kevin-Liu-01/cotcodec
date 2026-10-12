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
    t = _task(E__titles=["Untitled 1 - LibreOffice Calc"],
              E__rewritten={"/home/user/x.xlsx": False},
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
        "o3_shift_detected": [True] * 95 + [False] * 5,
        "o2_swap_detected": [True] * 89 + [False] * 11,
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
    smoke = root / "program/evidence/2026-10-11/s2v4-image/smoke-1197"
    records = I.load_records([smoke / "probes.jsonl"])
    pool = json.loads((root / "program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/"
                       "compute/pool/pool-v3.json").read_text())  # fmt: skip
    tasks = I.tasks_from_records(records, I.strict_titles(pool))
    assert len(tasks) == 3 and all(set(t["cells"]) == set(K.ADMISSION_CELLS) for t in tasks)
    e = tasks[0]["cells"]["E"]
    assert e["observed"] and e["titles"] and e["donothing"] == "fail"
    assert all(e["rewritten"].values())
    # smoke 1197 ran no gold slots: every task lacks a passing-side control there; every other
    # pool task has no record and is listed, unobserved, so excluded
    rows = {r["task_id"]: r for r in I.admission(records, pool)}
    assert len(rows) == 106
    smoke_ids = {t["task_id"] for t in tasks}
    assert [rows[t]["status"] for t in sorted(smoke_ids)] == ["runnable"] * 3
    others = [r for t, r in rows.items() if t not in smoke_ids]
    assert all(r["status"] == "excluded" and r["reasons"][0].startswith("unobserved:")
               for r in others)


def test_p010_from_the_reader_records():
    from harness.s2_locale import k0_inputs as I

    tid = "2cd43775-7085-45d8-89fa-9e35c0a915cf"
    key = "/org.openoffice.Office.Common/Save/Document|AutoSaveTimeIntervall"

    def rec(cell, value):
        return {"task_id": tid, "cell": cell, "kind": "capture", "attempt": 1,
                "slot": f"2cd43775:{cell}:r1", "status": "probed", "verdict": "fail",
                "p010": {"values": {key: value}}}

    same = [rec(c, []) for c in K.ADMISSION_CELLS]
    assert I.tasks_from_records(same, {})[0]["p010_pass"] is True
    differs = [rec(c, ["3"] if c == "AR" else []) for c in K.ADMISSION_CELLS]
    assert I.tasks_from_records(differs, {})[0]["p010_pass"] is False
    assert I.tasks_from_records(same[:-1], {})[0]["p010_pass"] is None  # PL has no reading
    assert "p010_pass" not in I.tasks_from_records(
        [{**r, "task_id": "x-1", "slot": r["slot"].replace("2cd43775", "x-1")} for r in same],
        {})[0]


def test_resumed_job_records_count_once():
    """``_run`` is the job's position in job order (``load_runs``)."""
    from harness.s2_locale import k0_inputs as I

    base = {"task_id": "t-1", "cell": "E", "kind": "capture", "slot": "t-1:E:r1", "attempt": 1}
    first = [{**base, "status": "cap_truncated", "_run": 0}]
    second = [{**base, "status": "probed", "verdict": "pass", "_run": 1}]
    assert I.counted(first + second)["t-1:E:r1"][-1]["verdict"] == "pass"
    done = [{**base, "status": "probed", "verdict": "fail", "_run": 0}]
    assert I.counted(done + second)["t-1:E:r1"][-1]["verdict"] == "fail"  # the first job stands
    assert I.counted(second + done)["t-1:E:r1"][-1]["verdict"] == "fail"  # record order is moot


def test_a_cut_requeue_is_not_final_and_the_resumed_job_reruns_the_slot():
    from harness.s2_locale import k0_inputs as I

    base = {"task_id": "t-1", "cell": "E", "kind": "capture", "slot": "t-1:E:r1"}
    lost = {**base, "attempt": 1, "status": "infrastructure", "_run": 0}
    cut = {**base, "attempt": 2, "status": "cap_truncated", "_run": 0}
    rerun = {**base, "attempt": 1, "status": "probed", "verdict": "pass", "_run": 1}
    assert not I.final_in_job([lost]) and not I.final_in_job([lost, cut])
    assert I.counted([lost, cut, rerun])["t-1:E:r1"] == [rerun]
    assert "t-1:E:r1" not in I.counted([lost, cut])  # unobserved until a job finishes it
    twice = {**base, "attempt": 2, "status": "infrastructure", "_run": 0}
    assert I.final_in_job([lost, twice])  # lost twice: final, and unobserved
    assert I.counted([lost, twice, rerun])["t-1:E:r1"] == [lost, twice]


def _lane_run(root, name, job, start=None, resumes=None, records=True, receipt=True):
    """A lane run directory as ``s2v4-vm.sbatch`` and the lane leave it: ``preflight.txt`` (the
    batch file's, before the lane starts), ``manifest.json``, and, when the lane got that far,
    ``probes.jsonl`` and ``lane-receipt.json``."""
    import json

    d = root / name
    d.mkdir(parents=True)
    (d / "preflight.txt").write_text(f"job_id={job}\nbatch_sha256={'0' * 64}\n")
    (d / "manifest.json").write_text(json.dumps({"resumes": {"job_id": resumes}}))
    if records:
        (d / "probes.jsonl").write_text(json.dumps({"slot": "t-1:E:r1", "status": "probed"}))
    if receipt:
        body = {"job_id": job} if start is None else {"job_id": job, "t_start": start}
        (d / "lane-receipt.json").write_text(json.dumps(body))
    return d


def test_run_order_follows_the_slurm_job_ids_the_batch_file_wrote(tmp_path):
    from harness.s2_locale import k0_inputs as I

    a, b = _lane_run(tmp_path, "1300", "1300", 1.0), _lane_run(tmp_path, "1301", "1301", 2.0,
                                                              resumes="1300")
    assert I.run_order([b, a]) == [a, b]
    ordered, records = I.load_runs([b, a])
    assert ordered == [a, b] and [r["_run"] for r in records] == [0, 1]
    with pytest.raises(I.RunOrderError, match="named twice"):
        I.run_order([a, a])
    with pytest.raises(I.RunOrderError, match="at most once"):
        I.load_runs([a, b, _lane_run(tmp_path, "1302", "1302", 3.0, resumes="1301")])


def test_run_order_needs_no_lane_receipt(tmp_path):
    """Round 4 (D90): a job ended by TERM (no receipt), one whose image check failed (a receipt,
    no records) and one with an old receipt without ``t_start`` are all read; the receipt is a
    cross-check only."""
    from harness.s2_locale import k0_inputs as I

    termed = _lane_run(tmp_path / "x", "1300", "1300", receipt=False)
    resume = _lane_run(tmp_path / "x", "1301", "1301", 5.0, resumes="1300")
    assert I.load_runs([resume, termed])[0] == [termed, resume]
    no_slot = _lane_run(tmp_path / "y", "1400", "1400", 1.0, records=False)
    resume2 = _lane_run(tmp_path / "y", "1401", "1401", resumes="1400")  # receipt without t_start
    ordered, records = I.load_runs([resume2, no_slot])
    assert ordered == [no_slot, resume2] and [r["_run"] for r in records] == [1]
    assert I.load_runs([no_slot]) == ([no_slot], [])  # zero records


def test_run_order_reads_the_oracle_mounts_by_their_preflight(tmp_path):
    """Inside the oracle's container the run directories are ``/ro/run1`` and ``/ro/run2``: the
    job order comes from ``preflight.txt``, whatever the mount names and the argument order."""
    from harness.s2_locale import k0_inputs as I

    census = _lane_run(tmp_path, "run2", "1300", receipt=False)  # mounted in the "wrong" order
    resume = _lane_run(tmp_path, "run1", "1301", 2.0, resumes="1300")
    assert I.run_order([resume, census]) == [census, resume]
    assert I.job_id(census) == 1300


def test_run_order_refusals(tmp_path):
    from harness.s2_locale import k0_inputs as I

    a = _lane_run(tmp_path, "1300", "1300", 20.0)
    later = _lane_run(tmp_path, "1301", "1301", 10.0, resumes="1300")  # a later id started earlier
    with pytest.raises(I.RunOrderError, match="different orders"):
        I.run_order([a, later])
    misnamed = _lane_run(tmp_path, "1302", "1303")
    with pytest.raises(I.RunOrderError, match="names job 1303"):
        I.run_order([misnamed])
    other = _lane_run(tmp_path, "1304", "1304", receipt=False)
    (other / "lane-receipt.json").write_text('{"job_id": "999", "t_start": 1.0}')
    with pytest.raises(I.RunOrderError, match="receipt names job"):
        I.run_order([other])
    bare = tmp_path / "1305"
    bare.mkdir()
    with pytest.raises(I.RunOrderError, match="no preflight.txt"):
        I.run_order([bare])
    (bare / "preflight.txt").write_text("job_id=\n")
    with pytest.raises(I.RunOrderError, match="no single Slurm job id"):
        I.run_order([bare])


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
    rows.append(rec("A", attempt=2, status="infrastructure",
                    infrastructure_type="probe:reset_task"))
    out = I.admission(rows, {"tasks": []})[0]
    assert out["status"] == "excluded" and "A1:A:setup_failed" in out["reasons"]
