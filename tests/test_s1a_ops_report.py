"""D59 (i) and (ii): the wrapper of the registered S1a report and its incomplete-data guard
(ops/s1a-analysis/run_report.py, check_identity.py), on synthetic records only.

Every test runs the registered ``analysis.main`` and the wrapper on the same data with the
same (reduced) resample counts, so byte identity is exact; the operator's full-constant check
on the dry run's lane-simulated scenarios is ``check_identity.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

from harness.q2_stage1 import analysis as A
from harness.q2_stage1 import estimators as E

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops" / "s1a-analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _s1a_ops_synth as SY  # noqa: E402
import check_identity as CI  # noqa: E402
import run_report as RR  # noqa: E402
import s1a_ops as O  # noqa: E402

N = 120


@pytest.fixture(autouse=True)
def _small(monkeypatch):
    monkeypatch.setattr(A, "N_BOOT", N)
    monkeypatch.setattr(A, "N_RANDOMIZATION", N)
    O.use_export(ROOT)


@pytest.fixture(scope="module")
def scenarios(tmp_path_factory):
    root = tmp_path_factory.mktemp("s1a-ops")
    return {
        name: SY.write_scenario(root / name, SY.make_records(**params))
        for name, params in SY.SCENARIOS.items()
    }


def registered(sc, out: Path) -> str | None:
    argv = [
        "--records",
        str(sc["records"]),
        "--plan",
        str(sc["plan"]),
        "--costs",
        str(sc["costs"]),
        "--out",
        str(out),
    ]
    try:
        A.main(argv)
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"
    return None


def wrapper(sc, out_dir: Path, costs: bool = True) -> dict:
    argv = [
        "--export",
        str(ROOT),
        "--records",
        str(sc["records"]),
        "--plan",
        str(sc["plan"]),
        "--out-dir",
        str(out_dir),
    ]
    if costs:
        argv += ["--costs", str(sc["costs"])]
    for path in sc["dr0"]:
        argv += ["--dr0", str(path)]
    assert RR.main(argv) == 0
    return {
        "guard": json.loads((out_dir / "guard.json").read_text()),
        "guarded": json.loads((out_dir / "report-guarded.json").read_text()),
        "report": out_dir / "report.json",
    }


def strip_guard(report: dict) -> dict:
    return {k: v for k, v in report.items() if k not in ("guard", "label")}


def test_widened_check_accepts_fractions_and_is_restored():
    y = np.full((2, 3, 2, 2, 2), 0.0)
    y[0, 0, 0, 0, 0] = 0.5
    with pytest.raises(ValueError, match="0, 1 or NaN"):
        E.delta(y)
    with RR.widened_check():
        assert np.isfinite(E.delta(y))
        bad = y.copy()
        bad[0, 0, 0, 0, 1] = 1.5
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            E.delta(bad)
        with pytest.raises(ValueError, match="shape"):
            E.delta(np.zeros((2, 2)))
    with pytest.raises(ValueError, match="0, 1 or NaN"):
        E.delta(y)
    binary = (np.random.default_rng(0).random((2, 6, 2, 2, 2)) < 0.4).astype(float)
    with RR.widened_check():
        assert np.array_equal(E._check(binary), np.asarray(binary, dtype=float))


@pytest.mark.parametrize(
    "name", ["null", "harness", "session", "floor", "dr0late", "baseincomplete"]
)
def test_report_is_byte_identical_to_the_registered_cli(scenarios, tmp_path, name):
    sc = scenarios[name]
    assert registered(sc, tmp_path / "registered.json") is None
    out = wrapper(sc, tmp_path / "w")
    assert out["report"].read_bytes() == (tmp_path / "registered.json").read_bytes()
    assert out["guard"]["registered_report"]["written"] is True
    assert out["guard"]["fractional_base_scores"] == 0


@pytest.mark.parametrize("name", ["null", "harness", "session", "floor"])
def test_complete_data_guarded_report_is_the_report_plus_a_guard(scenarios, tmp_path, name):
    out = wrapper(scenarios[name], tmp_path / "w")
    report = json.loads(out["report"].read_text())
    assert out["guard"]["label"] is None and out["guard"]["readings"] == []
    assert out["guard"]["labels"] == {
        "incomplete": None,
        "incomplete_reasons": [],
        "external_anchor": A.NOT_ANCHORED,
    }
    assert "label" not in out["guarded"]
    assert strip_guard(out["guarded"]) == report
    assert out["guarded"]["guard"]["completeness"]["incomplete"] is False


def test_fractional_scores_change_only_the_fractional_outputs(scenarios, tmp_path):
    sc = scenarios["fractional"]
    error = registered(sc, tmp_path / "registered.json")
    assert error is not None and "outcomes must be 0, 1 or NaN" in error  # bug B1
    out = wrapper(sc, tmp_path / "w")
    assert out["guard"]["fractional_base_scores"] == 5
    zeroed = tmp_path / "zeroed.jsonl"
    rows = CI.scored_zero(O.read_jsonl(sc["records"]))
    zeroed.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert registered({**sc, "records": zeroed}, tmp_path / "registered-zero.json") is None
    paths = CI.differing_paths(
        json.loads(out["report"].read_text()),
        json.loads((tmp_path / "registered-zero.json").read_text()),
    )
    assert "/fractional_score" in paths
    assert any(p.endswith("/fractional_scores") for p in paths)
    assert all(p.rsplit("/", 1)[-1] in CI.ALLOWED_LEAVES for p in paths), paths
    rep = json.loads(out["report"].read_text())
    assert rep["fractional_score"] is not None


def test_scored_zero_keeps_every_mismatch_flag():
    rows = [
        {"status": "scored", "score": 0.83, "offline_raw_score": 0.83},
        {"status": "scored", "score": 0.83, "offline_raw_score": 0.0},
        {"status": "scored", "score": 0.83, "offline_raw_score": 0.5},
        {"status": "scored", "score": 0.83, "offline_raw_score": 1.0},
        {"status": "scored", "score": 1.0, "offline_raw_score": 0.4},
        {"status": "infrastructure", "score": None},
    ]
    zeroed = CI.scored_zero(rows)
    for a, b in zip(rows, zeroed, strict=True):
        if a.get("offline_raw_score") is not None:
            assert (float(a["offline_raw_score"]) != float(a["score"])) == (
                float(b["offline_raw_score"]) != float(b["score"])
            )
    assert [r.get("score") for r in zeroed] == [0.0, 0.0, 0.0, 0.0, 1.0, None]


@pytest.mark.parametrize("name", ["dr0", "s2allinfra"])
def test_no_size_with_two_sessions_gives_the_delta_only_report(scenarios, tmp_path, name):
    sc = scenarios[name]
    error = registered(sc, tmp_path / "registered.json")
    assert error is not None and error.startswith("TypeError")  # bug B2 (rules.dr5)
    out = wrapper(sc, tmp_path / "w")
    assert not out["report"].exists()
    assert out["guard"]["registered_report"]["error"].startswith("TypeError")
    g = out["guarded"]
    assert g["label"] == RR.INCOMPLETE and out["guard"]["label"] == RR.INCOMPLETE
    assert out["guard"]["completeness"]["sizes_with_two_sessions"] == []
    prim = g["primary"]
    assert set(prim["estimates"]) == set(RR.DELTA_NAMES)
    assert prim["estimates"]["delta"]["estimate"] is not None
    assert isinstance(prim["tests"]["delta_paired_t"]["p"], float)
    for item in ("D_b", "D_w", "DR2", "DR5", "P1", "P2"):
        assert item in prim["not_estimable"]
    text = json.dumps(g)
    assert "x_signflip_p" not in text and "session_signflip_p" not in text
    for p in ("P1", "P2", "P3"):
        assert "not_estimable" in g["predictions"][p]
    if name == "dr0":  # 4B never ran: DR1 and P4 cannot be read
        assert "not_estimable" in prim["DR1_drop_4B"]
        assert "not_estimable" in g["predictions"]["P4"]
    else:  # 4B holds session 1 only
        assert prim["DR1_read_on_sessions"] == ["S1"]
        assert g["predictions"]["P4"]["incomplete_note"] == "DR1 read on S1 only"
    assert g["predictions"]["P5"]["read"] == "DR4"
    assert g["external_anchor"]["label"] == A.NOT_ANCHORED
    assert g["cells"] and g["attempts"] and "checker_noise" in g
    # the delta estimate equals the registered statistic on the same array
    y = A.R.outcome_array(A.R.final_records(A.R.read_jsonl(sc["records"])), SY.BASE)
    assert prim["estimates"]["delta"]["estimate"] == A._f(E.delta(y))
    assert prim["tests"]["delta_paired_t"]["p"] == A._f(E.paired_t(E.task_delta(y))["p"])


def test_registered_x_test_on_all_nan_data_is_spurious_and_masked():
    """Bug B2's mechanism: on an all-NaN statistic the sign flip returns 1/(n+1)."""
    y = np.full((2, 6, 2, 2, 2), np.nan)
    y[:, :, :, 0, :] = (np.random.default_rng(1).random((2, 6, 2, 2)) < 0.5).astype(float)
    p = float(E.x_signflip_p(y, 99, np.random.default_rng(42)))
    assert p == pytest.approx(0.01)
    comp = {
        "sizes_with_two_sessions": [],
        "sizes_without_two_sessions": ["4B", "9B"],
        "sizes": {"4B": {"sessions": ["S1"]}, "9B": {"sessions": ["S1"]}},
    }
    block = {
        "tasks": 6,
        "tests": {
            "delta_paired_t": {"p": 0.5},
            "delta_paired_t_by_size": [{"p": 0.5}, {"p": 0.5}],
            "x_signflip_p": p,
            "x_label_permutation_p_sensitivity": p,
            "session_signflip_p": [p, p],
        },
        "DR2": {"class": "Present"},
        "DR5": {"outcome": "GO"},
        "estimates": {"pi_9B": {"estimate": None, "one_sided_95": [None, None]}},
    }
    guarded, notes = RR.mask_block(block, y, comp)
    assert "not_estimable" in guarded["tests"]["x_signflip_p"]
    assert "not_estimable" in guarded["tests"]["x_label_permutation_p_sensitivity"]
    assert all("not_estimable" in v for v in guarded["tests"]["session_signflip_p"])
    assert "not_estimable" in guarded["DR2"]
    assert guarded["DR5"]["outcome"] == RR.DR5_NOT_EVALUABLE
    assert notes


def test_single_session_size(scenarios, tmp_path):
    """A1-4B-S2 never runs (as when DR0 fires at A1-9B-S2): 4B holds session 1 only (bug B3)."""
    sc = scenarios["dr0late"]
    out = wrapper(sc, tmp_path / "w")
    report = json.loads(out["report"].read_text())
    # the registered report shows a spurious 4B session p-value (1/(n+1))
    assert report["primary"]["tests"]["session_signflip_p"][0] == pytest.approx(
        1 / (N + 1), abs=1e-6
    )
    assert report["primary"]["pi_small_rule"] == "mean of pi_4B and pi_9B"
    comp = out["guard"]["completeness"]
    assert comp["incomplete"] is True and comp["jobs_absent"] == ["A1-4B-S2"]
    assert comp["sizes"]["4B"]["sessions"] == ["S1"] and comp["sizes_with_two_sessions"] == ["9B"]
    g = out["guarded"]
    assert g["label"] == RR.INCOMPLETE
    for name in RR.SET_ORDER:
        block = g[name]
        assert "not_estimable" in block["tests"]["session_signflip_p"][0]
        assert isinstance(block["tests"]["session_signflip_p"][1], float)
        assert block["DR5"]["outcome"] == RR.DR5_NOT_EVALUABLE
        assert block["DR1_read_on_sessions"] == ["S1"]
        # each pooled estimate states the sizes it averages: D_w and delta take 4B's session 1
        pooled = block["pooled_from_sizes"]["sizes"]
        assert pooled["D_w"] == ["4B", "9B"] and pooled["delta"] == ["4B", "9B"]
        for est in ("D_b", "excess", "X", "pi_mean_4B_9B", "D_b_same_block", "D_b_cross_block"):
            assert pooled[est] == ["9B"], est
        assert "pooled D_w is descriptive" in block["pooled_from_sizes"]["note"]
        assert "4B holds S1" in block["pooled_from_sizes"]["note"]
    prim = g["primary"]
    assert prim["DR1_drop_4B"] is False and prim["registered_pi_small_defined"] is False
    assert prim["pi_small_rule_note"].startswith("4B lacks two sessions: the registered pi_small")
    assert "is undefined; the value shown is the mean over 9B" in prim["pi_small_rule_note"]
    assert "the X test reads 9B alone" in prim["DR2"]["incomplete_note"]
    # the pooled values are the registered ones, unchanged
    rep_est, g_est = report["primary"]["estimates"], prim["estimates"]
    assert g_est["D_w"] == rep_est["D_w"] and g_est["D_b"] == rep_est["D_b_9B"] == rep_est["D_b"]
    desc = g["primary"]["DR5"]["description_only"]
    assert set(desc["against_M"]) == {"M_SMALL", "M_9B"}
    assert {v["M"] for v in desc["against_M"].values()} == {0.13, 0.18}
    assert desc["pi_9B"] == report["primary"]["estimates"]["pi_9B"]
    assert "GO" not in json.dumps(g["primary"]["DR5"]).replace("NO-GO", "")
    assert g["predictions"]["P1"]["incomplete_note"] == "pooled over 9B only"
    assert g["predictions"]["P4"]["incomplete_note"] == "DR1 read on S1 only"
    assert out["guard"]["readings"][0].startswith("every output labelled incomplete")
    guard = out["guard"]
    assert guard["labels"]["incomplete"] == RR.INCOMPLETE
    assert guard["labels"]["external_anchor"] == A.NOT_ANCHORED
    assert "must not be read directly" in guard["read"]
    assert set(guard["interpretation"]) >= {"that_size", "one_size_with_one_session"}
    assert g["guard"]["labels"] == guard["labels"]


def test_single_session_size_where_dr1_drops_4b(scenarios, tmp_path):
    """4B holds session 1 only and is at the floor there: DR1 (read on S1) drops 4B, so the
    registered pi_small is pi_9B; DR5 is still not evaluable as registered (D59 (ii))."""
    out = wrapper(scenarios["dr0latefloor"], tmp_path / "w")
    report = json.loads(out["report"].read_text())
    assert report["primary"]["DR1_drop_4B"] is True
    assert report["primary"]["pi_small_rule"] == "pi_9B (DR1 drops 4B)"
    prim = out["guarded"]["primary"]
    assert prim["registered_pi_small_defined"] is True
    note = prim["pi_small_rule_note"]
    assert "DR1 drops 4B, so the registered pi_small is pi_9B" in note and "undefined" not in note
    assert "DR5 is not evaluable as registered" in note
    assert "registered pi_small is pi_9B" in prim["DR2"]["incomplete_note"]
    assert prim["DR5"]["outcome"] == RR.DR5_NOT_EVALUABLE
    assert prim["DR1_read_on_sessions"] == ["S1"]
    assert out["guarded"]["predictions"]["P4"]["incomplete_note"] == "DR1 read on S1 only"


def test_dr0_on_the_last_job_labels_incomplete_but_keeps_two_sessions(scenarios, tmp_path):
    sc = scenarios["baseincomplete"]
    out = wrapper(sc, tmp_path / "w")
    comp = out["guard"]["completeness"]
    assert comp["dr0_fired"] == ["A1-4B-S2"]
    assert (
        comp["jobs"]["A1-4B-S2"]["dr0_fires"] and comp["jobs"]["A1-4B-S2"]["dr0_from_records_fires"]
    )
    assert comp["sizes_with_two_sessions"] == ["4B", "9B"]
    g = out["guarded"]
    report = json.loads(out["report"].read_text())
    assert g["label"] == RR.INCOMPLETE
    assert (
        g["primary"]["DR5"] == report["primary"]["DR5"]
    )  # evaluable: both sizes hold two sessions
    assert strip_guard(g) == report
    readings = out["guard"]["readings"]
    assert readings[0] == "every output labelled incomplete: DR0 fired for A1-4B-S2"
    assert readings[1].startswith("A1-4B-S2 fired DR0, but 4B holds scored base records in both")
    assert "4B's session test, DR1, DR5 kept as the registered code" in readings[1]
    assert "interpretation 'that_size'" in readings[1] and len(readings) == 2


def test_without_costs_p5_is_not_evaluated(scenarios, tmp_path):
    out = wrapper(scenarios["null"], tmp_path / "w", costs=False)
    report = json.loads(out["report"].read_text())
    assert report["predictions"]["P5"] == {"falsified": False, "read": "DR4"}  # bug B8
    assert "not_estimable" in out["guarded"]["predictions"]["P5"]


def test_every_job_needs_its_dr0_output(scenarios, tmp_path):
    sc = scenarios["null"]
    argv = [
        "--export",
        str(ROOT),
        "--records",
        str(sc["records"]),
        "--plan",
        str(sc["plan"]),
        "--out-dir",
        str(tmp_path / "w"),
        "--dr0",
        str(sc["dr0"][0]),
    ]
    with pytest.raises(SystemExit, match="no DR0 output"):
        RR.main(argv)


def test_outputs_are_never_overwritten(scenarios, tmp_path):
    wrapper(scenarios["null"], tmp_path / "w")
    with pytest.raises(SystemExit, match="exists"):
        wrapper(scenarios["null"], tmp_path / "w")


def in_process_runner(records, plan, costs, out):
    argv = ["--records", str(records), "--plan", str(plan), "--out", str(out)]
    if costs:
        argv += ["--costs", str(costs)]
    try:
        A.main(argv)
    except Exception as exc:  # noqa: BLE001
        return 1, f"{type(exc).__name__}: {exc}"
    return 0, ""


@pytest.mark.parametrize(
    "name, mode, passes",
    [
        ("null", "byte identity", True),
        ("fractional", "fractional", True),
        ("dr0", "registered report failed", True),
    ],
)
def test_check_identity(scenarios, tmp_path, name, mode, passes):
    sc = scenarios[name]
    wrapper(sc, tmp_path / "w")
    result = CI.check(
        sc["records"],
        sc["plan"],
        sc["costs"],
        tmp_path / "w" / "report.json",
        tmp_path / "identity",
        in_process_runner,
    )
    assert result["mode"].startswith(mode)
    assert result["pass"] is passes


def test_check_identity_catches_a_difference(scenarios, tmp_path):
    sc = scenarios["null"]
    wrapper(sc, tmp_path / "w")
    report = tmp_path / "w" / "report.json"
    report.write_text(report.read_text().replace('"conditional_on"', '"conditional_ON"'))
    result = CI.check(
        sc["records"], sc["plan"], sc["costs"], report, tmp_path / "identity", in_process_runner
    )
    assert result["pass"] is False
