"""The registered S1a report end to end on synthetic episode records."""

from __future__ import annotations

import json

import numpy as np
import pytest

from harness.q2_stage1 import analysis as A
from harness.q2_stage1 import estimators as E
from harness.q2_stage1 import records as R

BASE = [f"b{i:02d}" for i in range(10)]
EXT = {"1": ["e01", "e02"], "2": ["e03", "e04"]}


def synthetic(p_osw: float, p_ga: float, seed: int, truncate_block2: bool = False):
    rng = np.random.default_rng(seed)
    out = []
    tasks = BASE + EXT["1"] + EXT["2"]
    for z in R.SIZES:
        for s in R.SESSIONS:
            for t in tasks:
                ext = next((int(b) for b, ts in EXT.items() if t in ts), None)
                for h, p in zip(R.HARNESSES, (p_osw, p_ga), strict=True):
                    for r in R.RERUNS:
                        base = {
                            "schema": R.SCHEMA, "job": f"A1-{z}-{s}", "size": z, "session": s,
                            "task_id": t, "harness": h, "rerun": r, "extension_block": ext,
                            "attempt": 1, "steps": 10, "truncated_steps": 2,
                            "truncated_no_tool_call_steps": 1,
                            "checker_input_sha256": f"{t}-{h}",
                        }  # fmt: skip
                        if truncate_block2 and ext == 2 and s == "S2":
                            out.append({**base, "status": "cap_truncated"})
                            continue
                        score = float(rng.random() < p)
                        out.append({**base, "status": "scored", "score": score})
    return out


PLAN = {"base": BASE, "extension_blocks": EXT, "flagged_tasks": ["b00"]}


def test_report_structure_and_sets():
    recs = synthetic(0.3, 0.3, 1, truncate_block2=True)
    rep = A.report(recs, PLAN, n_boot=200, n_rand=200)
    assert rep["primary"]["tasks"] == 10
    assert rep["sensitivity_flagged_tasks_excluded"]["tasks"] == 9
    sec = rep["secondary_base_plus_completed_extension"]
    assert sec["blocks"] == [1] and sec["tasks"] == 12
    est = rep["primary"]["estimates"]
    for name in ("delta", "D_b", "D_w", "excess", "X", "X_centred_4B", "pi_small",
                 "session_shift_9B", "D_b_same_block", "D_b_cross_block"):  # fmt: skip
        assert set(est[name]) == {"estimate", "ci95", "one_sided_95"}
    assert set(rep["predictions"]) == {"P1", "P2", "P3", "P4", "P5"}
    # Section 15's label reads the cap hits without a complete tool call (A0a's gate).
    assert rep["truncation"]["share"]["9B/H-GA"] == pytest.approx(0.1)
    assert rep["truncation"]["share_any_cap_hit"]["9B/H-GA"] == pytest.approx(0.2)
    assert rep["checker_noise"]["discordant_pairs_identical_checker_inputs"] > 0
    assert rep["primary"]["DR5"]["share"] == "pi_small"
    json.dumps(rep)  # the report serialises


def test_extreme_harness_effect_is_present_and_go():
    recs = synthetic(0.0, 1.0, 2)
    rep = A.report(recs, PLAN, n_boot=200, n_rand=500)
    prim = rep["primary"]
    assert prim["estimates"]["delta"]["estimate"] == 1.0
    assert prim["tests"]["x_signflip_p"] < 0.01
    assert prim["DR2"]["class"] == "Present"
    assert prim["DR5"]["outcome"] == "GO"
    assert rep["predictions"]["P3"]["falsified"] is True


def test_floor_drops_4b_and_switches_the_share():
    recs = [r for r in synthetic(0.0, 0.0, 3) if r["size"] == "4B"]
    recs += [r for r in synthetic(0.3, 0.6, 4) if r["size"] == "9B"]
    rep = A.report(recs, PLAN, n_boot=200, n_rand=200)
    assert rep["primary"]["DR1_drop_4B"] is True
    assert rep["primary"]["DR5"]["share"] == "pi_9B"
    assert rep["predictions"]["P4"]["falsified"] is True


def test_dr2_reads_pi_9b_when_dr1_drops_4b(monkeypatch):
    """Section 9 item 4: with 4B at the floor, pi_small is pi_9B, so DR2's Near-equivalent
    bound is pi_9B's, not half of it (the two-size mean with pi_4B = 0)."""
    rng = np.random.default_rng(11)
    y = np.zeros((2, 32, 2, 2, 2))
    effect = rng.choice([-0.35, 0.0, 0.35], size=32)  # task-specific harness effects in 9B
    base = rng.uniform(0.2, 0.6, size=32)
    for h, sign in ((0, -0.5), (1, 0.5)):
        p = np.clip(base + sign * effect, 0, 1)[:, None, None]
        y[1, :, h] = (rng.random((32, 2, 2)) < p).astype(float)
    seen = {}
    real = A.rules.dr2

    def spy(p_delta, p_x, ci90, pi_small_ub95):
        seen["ub"] = pi_small_ub95
        return real(p_delta, p_x, ci90, pi_small_ub95)

    monkeypatch.setattr(A.rules, "dr2", spy)
    out = A.analyse_array(y, n_boot=400, n_rand=200)
    est = out["estimates"]
    assert seen["ub"] == est["pi_9B"]["one_sided_95"][1]  # not the two-size mean's bound
    assert out["DR1_drop_4B"] is True and est["pi_4B"]["estimate"] == 0.0
    assert est["pi_small"]["estimate"] == est["pi_9B"]["estimate"] > 0
    assert est["pi_small"]["one_sided_95"] == est["pi_9B"]["one_sided_95"]
    assert out["pi_small_rule"].startswith("pi_9B")
    assert est["pi_mean_4B_9B"]["estimate"] == pytest.approx(est["pi_9B"]["estimate"] / 2, abs=1e-5)
    assert est["pi_mean_4B_9B"]["one_sided_95"][1] < est["pi_9B"]["one_sided_95"][1]
    assert out["DR5"]["share"] == "pi_9B"


def test_metric_exception_sensitivity_and_divergence():
    recs = synthetic(0.5, 0.5, 5)
    recs[0] = {**recs[0], "score": 0.0, "metric_exception": True}
    rep = A.report(recs, PLAN, n_boot=100, n_rand=100, step_logs={
        ("4B", "S1", "b00", "H-GA", 1): [{"prompt_sha256": "a", "ir_sha256": "x"}],
        ("4B", "S1", "b00", "H-GA", 2): [{"prompt_sha256": "a", "ir_sha256": "y"}],
        ("4B", "S2", "b00", "H-GA", 1): [{"prompt_sha256": "b", "ir_sha256": "x"}],
    })  # fmt: skip
    assert rep["cells"]["4B/H-OSW-fixed"]["metric_exceptions"] == 1
    assert rep["first_divergence"]["within"] == {"serving": 1}
    assert rep["first_divergence"]["between"] == {"environment": 2}


def test_bootstrap_draws_match_the_point_estimate_on_identity_resample():
    rng = np.random.default_rng(0)
    y = (rng.random((2, 8, 2, 2, 2)) < 0.4).astype(float)
    stats = A.statistics(y)
    assert stats["pi_small"] == pytest.approx(float(np.nanmean(E.pi_by_size(y))))
    assert stats["excess"] == pytest.approx(float(np.mean(E.d_between(y) - E.d_within(y))))


def test_cli_refuses_to_overwrite(tmp_path):
    recs = synthetic(0.3, 0.3, 6)
    path = tmp_path / "a1.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in recs))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(PLAN))
    out = tmp_path / "report.json"
    out.write_text("{}")
    with pytest.raises(SystemExit):
        A.main(["--records", str(path), "--plan", str(plan), "--out", str(out)])


def test_corrected_verdicts_domains_and_the_truncation_mediator():
    recs = synthetic(0.3, 0.3, 7)
    for i, r in enumerate(recs):
        if r["task_id"] == "b01" and r["status"] == "scored" and r["score"] == 0.0:
            recs[i] = {**r, "corrected_score": 1.0}
        if r["task_id"] == "b02":
            recs[i] = {**r, "truncated_steps": 0}
    plan = {**PLAN, "task_domains": {t: ("calc" if t < "b05" else "impress") for t in BASE}}
    rep = A.report(recs, plan, n_boot=100, n_rand=100)
    flips = rep["checker_corrected"]["flips_per_task"]
    assert set(flips) == {"b01"} and flips["b01"] > 0
    assert rep["checker_corrected"]["tasks"] == 10
    assert set(rep["per_domain"]) == {"calc", "impress"}
    assert rep["per_domain"]["calc"]["tasks"] == 5
    # every episode but b02's has a truncated step, so the mediator delta rests on b02
    assert rep["truncation"]["delta_without_truncated_episodes_mediator_description"] is not None
    with pytest.raises(ValueError):
        R.outcome_array({}, ["b00"], value="other")


def _anchor(task, status="scored", score=1.0, attempt=1):
    rec = {"schema": R.ANCHOR_SCHEMA, "task_id": task, "attempt": attempt, "status": status}
    if status == "scored":
        rec["score"] = score
    if status == "infrastructure":
        rec["infrastructure_type"] = "vm_boot"
    return rec


def test_anchor_report_reads_the_completed_prefix():
    rng = np.random.default_rng(1)
    order = [f"a{i:03d}" for i in range(70)]
    public = {t: [float(v) for v in (rng.random(3) < 0.25)] for t in order}
    recs = [_anchor(t, score=public[t][0]) for t in order[:66]]
    recs.append(_anchor(order[66], status="cap_truncated"))
    recs.append(_anchor(order[3], status="infrastructure"))
    recs[3] = _anchor(order[3], status="infrastructure")
    out = A.anchor_report(recs, order, public, excluded=[order[5]])
    assert out["tasks_read"] == 64  # 66 completed, one lost in the prefix, one excluded
    assert out["outcome"] in ("ANCHOR-PASS", "ANCHOR-FAIL")
    assert out["lost_in_prefix"] == [order[3]]
    assert len(out["discordance_ours_vs_public"]) == 3
    short = A.anchor_report(recs[:50], order, public)
    assert short["outcome"] == "ANCHOR-INCOMPLETE"
    bad = [_anchor(t, score=0.0) for t in order]
    assert A.anchor_report(bad, order, public)["outcome"] == "ANCHOR-FAIL"
    with pytest.raises(R.RecordError):
        R.validate_anchor({"schema": "x"})


def test_cli_writes_the_report_with_costs_and_anchor(tmp_path, monkeypatch):
    recs = synthetic(0.3, 0.4, 8)
    path = tmp_path / "a1.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in recs))
    order = [f"a{i:03d}" for i in range(60)]
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({**PLAN, "anchor_tasks": order}))
    costs = tmp_path / "costs.json"
    costs.write_text(json.dumps({"A1-9B-S1": {"gpu_h_per_episode": 0.0125, "V": 20}}))
    anchor = tmp_path / "anc.jsonl"
    anchor.write_text("\n".join(json.dumps(_anchor(t)) for t in order))
    public = tmp_path / "public.json"
    public.write_text(json.dumps({t: [1.0, 1.0, 0.0] for t in order}))
    out = tmp_path / "report.json"
    args = ["--records", str(path), "--plan", str(plan), "--costs", str(costs)]
    args += ["--anchor", str(anchor), "--public", str(public), "--out", str(out)]
    monkeypatch.setattr(A, "N_BOOT", 200)
    monkeypatch.setattr(A, "N_RANDOMIZATION", 200)
    assert A.main(args) == 0
    rep = json.loads(out.read_text())
    assert rep["DR4"]["jobs"] == ["A1-9B-S1"] and rep["predictions"]["P5"]["falsified"]
    assert rep["anchor"]["tasks_read"] == 60


def test_realized_costs_follow_section_9_item_10(tmp_path):
    """GPU-h per episode = the GPU job's Slurm elapsed hours over its episodes that ran to an
    end (scored or infrastructure, base and fill); per harness by slot-occupancy share."""
    rows = []
    for i in range(10):
        h = R.HARNESSES[i % 2]
        status = "cap_truncated" if i == 9 else ("infrastructure" if i == 0 else "scored")
        rows.append({"job": "A1-9B-S1", "size": "9B", "harness": h, "status": status,
                     "host": {"slot_occupancy_s": 600.0 if h == "H-GA" else 300.0}})  # fmt: skip
    rows.append({"job": "A1-4B-S1", "size": "4B", "harness": "H-GA", "status": "scored"})
    c = A.realized_costs(rows, job="A1-9B-S1", v=20, gpu_elapsed_s=0.9 * 3600)
    assert c["episodes"] == 9 and c["gpu_h_per_episode"] == pytest.approx(0.1)
    osw, ga = c["by_harness"]["H-OSW-fixed"], c["by_harness"]["H-GA"]
    assert (osw["episodes"], ga["episodes"]) == (5, 4)
    assert osw["gpu_h_share"] == pytest.approx(1500 / 3900, abs=1e-6)
    assert ga["gpu_h_per_episode"] == pytest.approx(2400 / 3900 * 0.9 / 4, abs=1e-6)
    assert c["vm_h_per_episode"] == pytest.approx(3900 / 3600 / 9, abs=1e-6)
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text(
        json.dumps(
            {"purpose": "a1", "vm": {"concurrency": 20}, "a1": {"size": "9B", "session": "S1"}}
        )
    )
    recs = [dict(r, schema=R.SCHEMA, session="S1", task_id="t", rerun=1, extension_block=None,
                 attempt=1, score=1.0 if r["status"] == "scored" else None,
                 infrastructure_type="transport" if r["status"] == "infrastructure" else None)
            for r in rows if r["job"] == "A1-9B-S1"]  # fmt: skip
    (run / "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    (run / "lane-receipt.json").write_text(json.dumps({"gpu_job": {"job_id": "88"}}))
    out = tmp_path / "costs.json"
    assert A.main(["costs", "--run-dir", str(run), "--elapsed", "A1-9B-S1=3240",
                   "--out", str(out)]) == 0  # fmt: skip
    costs = json.loads(out.read_text())
    assert costs["A1-9B-S1"]["gpu_h_per_episode"] == pytest.approx(0.1)
    assert A.costs_by_size(costs)["9B"]["episodes"] == 9
    assert rules_dr4(costs) == ["A1-9B-S1"]  # above the V = 20 high price


def rules_dr4(costs):
    from harness.q2_stage1 import rules

    return rules.dr4({j: (c["gpu_h_per_episode"], c["V"]) for j, c in costs.items()})["jobs"]


def test_report_labels_an_unanchored_run():
    rep = A.report(synthetic(0.3, 0.3, 9), PLAN, n_boot=50, n_rand=50)
    assert rep["external_anchor"] == {"outcome": "ANCHOR-UNAVAILABLE",
                                      "label": "not externally anchored"}  # fmt: skip


def test_checker_noise_reads_the_merged_offline_verdict():
    """``rescore.merge`` writes ``offline_raw_score``; a live-versus-offline mismatch counts."""
    recs = synthetic(0.5, 0.5, 12)
    scored = [i for i, r in enumerate(recs) if r["status"] == "scored"]
    recs[scored[0]] = {**recs[scored[0]], "offline_raw_score": 1.0 - recs[scored[0]]["score"]}
    recs[scored[1]] = {**recs[scored[1]], "offline_raw_score": recs[scored[1]]["score"]}
    finals = R.final_records(recs)
    assert A.checker_noise(finals)["live_vs_offline_mismatches"] == 1
