"""Registered headline analysis, K2 sample, probe-informed cells and infra causes."""

from __future__ import annotations

from typing import Any

import pytest

from harness.q2_mutation import analysis, campaign, offline_eval
from harness.q2_mutation.operators import all_operators


def _row(n: int, task: str, label: str, verdict: str, family: str = "f", **extra: Any) -> dict:
    event = {
        ("should_pass_equiv", False): "FN",
        ("should_pass_alt_solution", False): "FN_alt",
        ("should_fail_violation", True): "FP_R",
        ("should_fail_extra_change", True): "FP_F",
    }.get((label, verdict == "pass"), "ok")
    return {
        "mutant_id": f"{task}__op__{n}",
        "task_id": task,
        "target_id": f"{task}__t",
        "label": label,
        "lock_status": "evaluable",
        "lock_verdict": verdict,
        "lock_event": event,
        "lock_null_verdict": "pass",
        "checker_family": family,
        "probe_touched": False,
        "operator": "op",
        "admitted": True,
        "post_save_admitted": True,
        **extra,
    }


def test_audit_gates_p2_alternatives_and_p4() -> None:
    rows = [
        _row(1, "t1", "should_pass_alt_solution", "fail"),
        _row(2, "t1", "should_pass_alt_solution", "fail"),
        _row(3, "t2", "should_fail_extra_change", "pass"),
        _row(4, "t2", "should_fail_extra_change", "pass"),
        _row(5, "t2", "should_fail_extra_change", "pass"),
        _row(6, "t3", "should_fail_extra_change", "fail"),
        _row(7, "t3", "should_pass_equiv", "fail", probe_touched=True),
    ]
    decisions = {
        "t1__op__1": "accept",
        "t1__op__2": "reject",
        "t2__op__3": "reject",
        "t2__op__4": "unresolved",
    }
    units, gate = analysis.metric_units(rows, decisions, "lock")
    # Accepted alternative solutions enter P2; the rejected one never does.
    assert units["P2"] == [("t1", "f", True)]
    # P4: a passed extra change counts only when the audit rejects the file;
    # unresolved and unsampled passes leave it; a failed one stays (no event).
    assert sorted(units["P4"]) == [("t2", "f", True), ("t3", "f", False)]
    assert gate["P2_alt_decisions"] == {"accept": 1, "reject": 1}
    assert gate["P4_passed_decisions"] == {"reject": 1, "unresolved": 1, "not_sampled": 1}
    assert len(gate["P4_unresolved_as_events"]) == 3


def test_family_floor_decides_k7_and_k6b() -> None:
    rows = []
    for t in range(10):
        rows += [
            _row(n, f"a{t}", "should_fail_violation", "pass" if n < 2 else "fail", "big")
            for n in range(3)
        ]
    for t in range(5):
        rows += [_row(n, f"b{t}", "should_fail_violation", "pass", "small") for n in range(3)]
    for t in range(30):
        rows.append(_row(0, f"c{t}", "should_pass_equiv", "pass", "wide"))
    out = analysis.headline(rows, n_boot=300)
    p3 = out["P3"]["by_family"]
    assert p3["big"]["inferential"] and p3["big"]["k7_unreliable"]
    # Five tasks are below the 8-task floor: descriptive, K7 does not apply.
    assert not p3["small"]["inferential"] and not p3["small"]["k7_unreliable"]
    wide = out["P2"]["by_family"]["wide"]
    assert wide["k6b_no_detected_error"] and wide["zero_event_upper_bound"] < 0.10
    assert out["P5"]["n"] == 45 and out["P5"]["events"] == 15


def test_k3_single_rule_and_k2_label() -> None:
    pending = analysis.headline_exclusions(None, None)
    assert pending["audit"] == "pending"
    assert pending["k2"]["label"] == analysis.K2_UNVERIFIED
    fired = analysis.headline_exclusions(
        {
            "kappa_fires": False,
            "k3_fires": {"should_pass_equiv": True, "should_fail_violation": False},
        },
        {
            "executor_commit": "x",
            "pairs": 80,
            "disagreements": [
                {"checker_family": "compare_table", "explanation": "nondeterministic"},
                {"checker_family": "compare_pptx_files", "explanation": None},
            ],
        },
    )
    assert set(fired["metrics_leaving_headline"]) == {"P2", "P5"}
    assert fired["k2"]["families_dropped"] == ["compare_pptx_files"]
    kappa = analysis.headline_exclusions({"kappa_fires": True, "k3_fires": {}}, None)
    assert set(kappa["metrics_leaving_headline"]) == {"P2", "P3", "P4", "P5"}


def test_p1_and_k6_from_the_controls() -> None:
    def v(verdict: str) -> dict:
        return {"verdict": verdict, "score": None, "error": None}

    exposed = {"placed_office": ["/home/user/a.docx"], "saves": [], "save_failures": []}
    tasks = {
        "g1": {"gold_raw_lock": v("pass"), "gold_saved_lock": v("fail"), "gold_save": exposed},
        "g2": {"gold_raw_lock": v("pass"), "gold_saved_lock": v("pass"), "gold_save": exposed},
        "g3": {
            "gold_raw_lock": v("pass"),
            "gold_saved_lock": v("pass"),
            "gold_save": {"placed_office": [], "saves": [], "save_failures": []},
        },
    }
    from harness.q2_mutation import report

    controls = {"tasks": tasks, "aggregate": report.aggregate(tasks)}
    out = analysis.headline(
        [_row(0, "t1", "should_pass_equiv", "pass")],
        controls=controls,
        decisions={"g1__p1_flip": "accept"},
        n_boot=50,
    )
    assert out["P1"]["raw_flips"]["events"] == 1 and out["P1"]["raw_flips"]["n"] == 2
    assert out["P1"]["confirmed_tasks"] == ["g1"] and out["P1"]["not_exposed"] == ["g3"]
    assert out["K6"]["adequacy_claim"] is False  # one P5 task is far below 59


def test_k9_and_k5() -> None:
    rows = [_row(0, f"t{n}", "should_pass_equiv", "pass") for n in range(4)]
    rows[0]["lock_null_verdict"] = "fail"
    rows[1]["post_save_admitted"] = False
    out = analysis.headline(rows, n_boot=50)
    assert out["K9"]["null_not_pass"] == 1 and out["K9"]["share"] == 0.25
    assert not out["K9"]["fires"]
    assert out["K5"]["op"] == {"checked": 4, "normalized": 1, "normalization_finding_only": False}


def test_probe_informed_operators_are_exploratory_everywhere() -> None:
    informed = {op.name for op in all_operators() if op.provenance == "probe_informed"}
    assert informed == campaign.PROBE_INFORMED_OPERATORS
    for name in informed:
        assert campaign.is_probe_touched({}, "any-task", name)
    assert not campaign.is_probe_touched({}, "any-task", "docx.viol.text_edit")


def _jobs(domains: dict[str, int]) -> tuple[list[dict], dict[str, str]]:
    jobs, domain_of = [], {}
    for domain, tasks in domains.items():
        for t in range(tasks):
            task = f"{domain}-{t}"
            domain_of[task] = domain
            for n in range(10):
                jobs.append(
                    {
                        "job_id": f"{task}__{n}",
                        "mutant_id": f"{task}__{n}",
                        "task_id": task,
                        "kind": "mutant" if n else "null",
                    }
                )
    return jobs, domain_of


def test_k2_sample_is_seeded_stratified_and_verdict_free() -> None:
    jobs, domain_of = _jobs(
        {"libreoffice_calc": 12, "libreoffice_impress": 8, "libreoffice_writer": 5}
    )
    first = campaign.k2_sample(jobs, domain_of)
    assert len(first) == campaign.K2_PAIRS
    assert first == campaign.k2_sample(list(reversed(jobs)), domain_of)
    by_domain: dict[str, int] = {}
    for row in first:
        by_domain[row["domain"]] = by_domain.get(row["domain"], 0) + 1
    assert set(by_domain) == set(domain_of.values()) and min(by_domain.values()) >= 20
    per_task: dict[str, int] = {}
    for row in first:
        per_task[row["task_id"]] = per_task.get(row["task_id"], 0) + 1
    assert max(per_task.values()) <= campaign.K2_PER_TASK
    assert campaign.k2_sample(jobs, domain_of, seed=43) != first
    with pytest.raises(campaign.CampaignError, match="3 domains"):
        campaign.k2_sample(*_jobs({"a": 5, "b": 5}))
    # A small pool fills past the per-task cap rather than coming up short.
    small, small_domains = _jobs({"a": 1, "b": 1, "c": 1})
    assert len(campaign.k2_sample(small, small_domains, n=24)) == 24


@pytest.mark.parametrize(
    ("run", "reason"),
    [
        ({"infra_timeout": True, "error": "Timeout after 300s"}, "timeout"),
        ({"error": "worker exit -9 without result"}, "worker_died"),
        ({"error": "LiveStateRequired: getter vm_window"}, "live_state_required"),
        ({"error": "OfflineNetworkRefused: https://x"}, "network_refused"),
        ({"error": "KeyError: 'B2'"}, None),
        ({"error": None}, None),
    ],
)
def test_infra_reasons_are_kept_apart_from_checker_errors(run: dict, reason: str | None) -> None:
    assert offline_eval.infra_reason(run) == reason


def _write(path, rows) -> None:
    import json

    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_s1_flips_need_five_agreeing_scorings_per_venv(tmp_path) -> None:
    from harness.q2_mutation import dependency_flips

    prefix = str(tmp_path / "mut")
    ids = ["a", "b", "c", "d"]
    lock = {"a": "pass", "b": "pass", "c": "pass", "d": "fail"}
    scout = {"a": "fail", "b": "fail", "c": "fail", "d": "fail"}
    for arm, verdicts in (("lock", lock), ("scout", scout)):
        _write(
            tmp_path / f"mut-verdicts-{arm}.jsonl",
            [{"mutant_id": i, "verdict": verdicts[i]} for i in ids],
        )
        _write(
            tmp_path / f"mut-notes-{arm}.jsonl",
            [{"mutant_id": i, "nondeterministic": i == "c"} for i in ids],
        )
    _write(tmp_path / "jobs.jsonl", [{"mutant_id": i, "files": {}} for i in ids])
    # c is already nondeterministic at repeat 2 and d agrees: only a and b are candidates.
    assert dependency_flips.candidates(prefix) == ["a", "b"]

    def score(jobs, s1_prefix, workers) -> None:
        sent = [json_row["mutant_id"] for json_row in _jsonl(jobs)]
        assert sent == ["a", "b"] and s1_prefix == f"{prefix}-s1"
        for arm in ("lock", "scout"):
            rows = []
            for i in sent:
                if arm == "lock":
                    scores = [1.0] * 5 if i == "a" else [1.0, 0.0, 1.0, 1.0, 1.0]
                else:
                    scores = [0.0] * 5
                rows.append(
                    {
                        "mutant_id": i,
                        "repeat_scores": scores,
                        "repeat_errors": [None] * 5,
                        "infra_failed": False,
                    }
                )
            _write(tmp_path / f"mut-s1-notes-{arm}.jsonl", rows)

    result = dependency_flips.run(tmp_path / "jobs.jsonl", prefix, 4, score=score)
    assert [r["mutant_id"] for r in result["confirmed"]] == ["a"]
    assert [r["mutant_id"] for r in result["unstable"]] == ["b"]
    assert (tmp_path / "mut-s1.json").is_file()


def _jsonl(path) -> list:
    import json

    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_s1_without_candidates_scores_nothing(tmp_path) -> None:
    from harness.q2_mutation import dependency_flips

    for arm in ("lock", "scout"):
        _write(
            tmp_path / f"raw-verdicts-{arm}.jsonl", [{"mutant_id": "t__gold", "verdict": "pass"}]
        )
    _write(tmp_path / "jobs.jsonl", [{"mutant_id": "t__gold", "files": {}}])

    def score(*_args) -> None:
        raise AssertionError("no candidate, no rescoring")

    result = dependency_flips.run(tmp_path / "jobs.jsonl", str(tmp_path / "raw"), 4, score=score)
    assert result["candidates"] == [] and result["confirmed"] == []
