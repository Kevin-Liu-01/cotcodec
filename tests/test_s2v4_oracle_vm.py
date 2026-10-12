"""S2 v4 oracle on VM renders: XML nodes, K0's masked counts, masked O5, plants, metrics."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from harness.s2_locale import k0_v4
from harness.s2_locale import oracle_vm as V

XML = """<desktop-frame xmlns:st="https://accessibility.ubuntu.example.org/ns/state"
 xmlns:cp="https://accessibility.ubuntu.example.org/ns/component">
<application name="gnome-shell"><frame name="x" cp:screencoord="(0, 0)" cp:size="(10, 10)"/>
</application>
<application name="soffice"><frame name="Doc - LibreOffice Calc" st:showing="true"
 cp:screencoord="(70, 27)" cp:size="(1850, 1053)">
<push-button name="Bold" st:showing="true" cp:screencoord="(100, 150)" cp:size="(30, 30)"/>
<document-spreadsheet name="" st:showing="true" cp:screencoord="(111, 281)" cp:size="(1738, 716)">
<table name="" cp:screencoord="(111, 281)" cp:size="(1738, 716)"/></document-spreadsheet>
<panel name="nobox"/></frame></application></desktop-frame>"""


def test_xml_nodes_are_the_v3_node_list():
    nodes = V.xml_nodes(XML)
    roles = [n["role"] for n in nodes]
    assert roles == ["frame", "push button", "document spreadsheet"]  # no gnome-shell, no table
    bold = nodes[1]
    assert bold["path"] == [1, 0, 0] and bold["box"] == [100, 150, 30, 30] and bold["showing"]
    assert nodes[2]["box"] == [111, 281, 1738, 716]


def _png(path: Path, arr: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.astype(np.uint8)).save(path)


def _render(root: Path, name: str, shot1: np.ndarray, shot2: np.ndarray | None = None) -> V.Render:
    d = root / name
    _png(d / "screens" / "post_setup-1.png", shot1)
    _png(d / "screens" / "post_setup-2.png", shot1 if shot2 is None else shot2)
    return V.Render(d)


def test_masked_counts_mask_the_top_bar_and_each_caret(tmp_path):
    base = np.full((1080, 1920, 3), 255, dtype=np.int16)
    other = base.copy()
    other[5:20, 100:200] = 0  # inside the GNOME top bar: masked
    other[500:510, 500:510] = 0  # 100 differing pixels
    other[600:620, 700:702] = 0  # the second render's caret, on in its first screenshot ...
    off = other.copy()
    off[600:620, 700:702] = 255  # ... and off in its second: its caret mask
    a = _render(tmp_path, "a", base)
    b = _render(tmp_path, "b", other, off)
    got = V.masked_counts(a, b)
    assert got["diff_pixels"] == 100 and got["exact_diff_pixels"] == 100
    faint = base.copy()
    faint[300:310, 300:310] = 245  # a channel difference of 10 is below the threshold
    assert V.masked_counts(a, _render(tmp_path, "c", faint))["diff_pixels"] == 0
    assert V.masked_counts(a, _render(tmp_path, "d", faint))["exact_diff_pixels"] == 100


def test_masked_o5_and_the_document_plant(tmp_path):
    from harness.s2_locale import phase0 as P0

    rng = np.random.default_rng(0)
    img = np.full((1080, 1920, 3), 255, dtype=np.int16)
    img[300:900, 200:1600] = rng.integers(0, 2, (600, 1400, 1)) * 200  # textured document
    box = [200, 300, 1400, 600]
    mask = np.zeros(img.shape[:2], dtype=bool)
    same = V.o5(img, mask, img.copy(), mask, box, 50)
    assert same["verdict"] == "pass" and same["unflipped"]["diff_pixels"] == 0
    planted = P0.plant_doc(img, box)
    hit = V.o5(img, mask, planted, mask, box, 50)
    assert V.detected(hit["verdict"]) and hit["unflipped"]["diff_pixels"] > 50
    # a caret mask over the plant hides it: masks apply in O5 too (K0)
    cover = np.zeros_like(mask)
    x, y = 200 + 1400 // 3, 300 + 600 // 3
    cover[y:y + 14, x:x + 48] = True
    assert V.o5(img, mask, planted, cover, box, 50)["verdict"] == "pass"
    assert not V.detected("pass") and not V.detected("uninformative_symmetric")


def test_metrics_feed_the_k0_instrument_checks():
    per_task = [
        {"task_id": "aaaaaaaa-1", "E_vs_S": {"diff_pixels": 0}, "E_vs_E2": {"diff_pixels": 3},
         "AD_vs_AR": {"diff_pixels": 0}, "o5_block_detected": True, "pd_detected": True,
         "o1": {"E-A": {"identical": True}, "ER-AR": {"identical": False}},
         "o4_parents": [True, True], "o3_shift_detected": True, "o2_swap_detected": False},
        {"task_id": "bbbbbbbb-2", "E_vs_S": {"diff_pixels": None}, "o5_block_detected": False},
    ]
    m = V.metrics(per_task, {"aa_dev": [3, 1]})
    assert m["e_vs_s"] == [0] and m["e_vs_e2"] == [3] and m["o5_block_detected"] == [True, False]
    assert m["pd_detected"] == {"aaaaaaaa": True} and m["o1_text_pairs"] == [True, False]
    checks = k0_v4.instrument_checks(m)
    assert checks["tol6"] == 50 and not checks["I1_doc"]["o5_block"]["pass"]


def test_task_generators_do_not_depend_on_order():
    a = V.task_rng("12382c62-0000").integers(1000)
    V.task_rng("e528b65e-0000").integers(1000)
    assert V.task_rng("12382c62-0000").integers(1000) == a


def test_render_index_takes_the_counted_probed_attempt(tmp_path):
    run = tmp_path / "run"
    rows = [
        {"slot": "aaaaaaaa:E:r1", "task_id": "aaaaaaaa-1", "cell": "E", "attempt": 1,
         "status": "infrastructure"},
        {"slot": "aaaaaaaa:E:r1", "task_id": "aaaaaaaa-1", "cell": "E", "attempt": 2,
         "status": "probed"},
        {"slot": "aaaaaaaa:E:r2", "task_id": "aaaaaaaa-1", "cell": "E", "attempt": 1,
         "status": "probed"},
        {"slot": "aaaaaaaa:E:g1", "task_id": "aaaaaaaa-1", "cell": "E", "attempt": 1,
         "status": "probed", "kind": "gold"},
    ]
    run.mkdir()
    (run / "probes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (run / "lane-receipt.json").write_text(json.dumps({"job_id": "1300", "t_start": 1.0}))
    index = V.render_index([run])
    assert index[("aaaaaaaa-1", "E", 1)] == run / "slots" / "aaaaaaaa_E_r1.a2"
    assert index[("aaaaaaaa-1", "E", 2)].name == "aaaaaaaa_E_r2.a1"
    assert len(index) == 2
    assert V.labelled_paths(index, "aaaaaaaa-1").keys() == {"E", "E2"}


@pytest.mark.parametrize("verdict", ["fail_changed", "fail_mirrored"])
def test_detected_verdicts(verdict):
    assert V.detected(verdict)


def _run(root: Path, job: str, t_start: float, rows: list, resumes: str | None = None) -> Path:
    run = root / job
    run.mkdir(parents=True)
    (run / "probes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (run / "lane-receipt.json").write_text(json.dumps({"job_id": job, "t_start": t_start}))
    manifest = {"purpose": "phase0"}
    if resumes:
        manifest.update(resume_from_block="b001", resumes={"job_id": resumes})
    (run / "manifest.json").write_text(json.dumps(manifest))
    return run


def test_render_index_reads_jobs_in_job_order_whatever_the_argument_order(tmp_path):
    """A slot both jobs finished counts from the earlier job (by Slurm job id and start time),
    never from the directory named first."""
    def rec(status, attempt=1):
        return {"slot": "aaaaaaaa:E:r1", "task_id": "aaaaaaaa-1", "cell": "E",
                "attempt": attempt, "status": status}

    first = _run(tmp_path, "1300", 10.0, [rec("probed")])
    second = _run(tmp_path, "1301", 20.0, [rec("probed")], resumes="1300")
    for order in ([first, second], [second, first]):
        index = V.render_index(order)
        assert index[("aaaaaaaa-1", "E", 1)] == first / "slots" / "aaaaaaaa_E_r1.a1"
    # a slot lost once, whose re-queue the interruption cut, is rerun by the resumed job
    cut = _run(tmp_path / "x", "1400", 10.0, [rec("infrastructure"), rec("cap_truncated", 2)])
    rerun = _run(tmp_path / "x", "1401", 20.0, [rec("probed")], resumes="1400")
    index = V.render_index([rerun, cut])
    assert index[("aaaaaaaa-1", "E", 1)] == rerun / "slots" / "aaaaaaaa_E_r1.a1"


def test_render_index_refuses_runs_without_a_job_order(tmp_path):
    from harness.s2_locale import k0_inputs

    row = {"slot": "aaaaaaaa:E:r1", "task_id": "aaaaaaaa-1", "cell": "E", "attempt": 1,
           "status": "probed"}
    a = _run(tmp_path, "1300", 20.0, [row])
    b = _run(tmp_path, "1301", 10.0, [row], resumes="1300")  # a later id that started earlier
    with pytest.raises(k0_inputs.RunOrderError, match="different orders"):
        V.render_index([a, b])
    (b / "lane-receipt.json").unlink()
    with pytest.raises(k0_inputs.RunOrderError, match="no lane-receipt"):
        V.render_index([a, b])
    c = _run(tmp_path, "1302", 30.0, [row], resumes="1299")
    with pytest.raises(k0_inputs.RunOrderError, match="not the resume"):
        V.render_index([a, c])


def test_registered_oracle_route_is_pinned():
    from harness.q2_stage1 import lane as s1a

    assert V.ORACLE_IMAGE_ID == s1a.EPISODE_IMAGE_ID  # the checker-mutation metric image
    argv = V.registered_argv(2)
    assert argv[:3] == [V.ORACLE_PYTHON, "-m", "harness.s2_locale.oracle_vm"]
    assert argv[argv.index("--runs") + 1:argv.index("--pool")] == ["/ro/run1", "/ro/run2"]
    assert (Path(__file__).resolve().parents[1] / V.POOL).is_file()
    assert "--k0" in argv and argv[argv.index("--out") + 1] == "/out/oracle.json"
    assert set(V.environment()) == {"python", "numpy", "scipy", "pillow"}
