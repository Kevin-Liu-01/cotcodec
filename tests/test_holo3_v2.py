from __future__ import annotations

import gzip
import hashlib
import io
import itertools
import json
import math
import tarfile
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from harness import holo3_v2 as v2
from harness import remote_zip
from harness.remote_zip import BytesSource
from tests._holo3_world import zip_bytes

# --------------------------------------------------------------------------- #
# Rule (d): evaluator classes
# --------------------------------------------------------------------------- #


def cfg(evaluator: dict, config: list | None = None) -> dict:
    return {"config": config or [], "evaluator": evaluator}


@pytest.mark.parametrize(
    ("config", "label", "reason", "narrow"),
    [
        (
            cfg({"func": "check", "expected": {"type": "rule_relativeTime", "rules": {}}}),
            "L",
            "getter:rule_relativeTime",
            True,
        ),
        (
            cfg(
                {
                    "func": "is_expected_tabs",
                    "result": {"type": "open_tabs_info"},
                    "expected": {"type": "info_from_website", "url": "https://www.example.com"},
                }
            ),
            "L",
            "getter:info_from_website",
            True,
        ),
        (
            cfg({"func": ["a", "b"], "result": [{"type": "active_tab_info"}, {"type": "vm_file"}]}),
            "L",
            "getter:active_tab_info",
            False,  # result side only: outside the plan's narrower L
        ),
        (
            cfg({"func": "compare_time_in_speedtest_results", "result": {"type": "vm_file"}}),
            "L",
            "metric:compare_time_in_speedtest_results",
            False,
        ),
        (
            cfg(
                {
                    "func": "check",
                    "expected": {
                        "type": "rule",
                        "rules": {"relativeTime": {"from": "next Monday"}},
                    },
                }
            ),
            "L",
            "rule:relativeTime",
            True,
        ),
        (
            cfg(
                {
                    "func": "check",
                    "postconfig": [
                        {
                            "type": "chrome_open_tabs",
                            "parameters": {"urls_to_open": ["https://www.example.com/x"]},
                        }
                    ],
                }
            ),
            "L",
            "postconfig:remote-url",
            False,
        ),
        (
            cfg(
                {
                    "func": "compare",
                    "expected": {"type": "cloud_file", "path": "https://example.org/gold.xlsx"},
                }
            ),
            "L",
            "getter:cloud_file:remote-url",
            True,
        ),
    ],
)
def test_live_or_clock_evaluators_are_class_l(
    config: dict, label: str, reason: str, narrow: bool
) -> None:
    result = v2.classify_evaluator(config)
    assert result.label == label
    assert reason in result.reasons
    assert result.narrow_l is narrow


def test_web_and_offline_classes() -> None:
    static_cache = (
        "https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/x.xlsx"
    )
    offline = cfg(
        {
            "func": "compare",
            "expected": {"type": "cloud_file", "path": static_cache},
            "result": {"type": "vm_file", "path": "/home/user/x.xlsx"},
        }
    )
    assert v2.classify_evaluator(offline).label == "O"
    assert v2.classify_evaluator(offline).narrow_l is False
    web = cfg(
        {"func": "is_expected_bookmarks", "result": {"type": "bookmarks"}},
        config=[
            {
                "type": "chrome_open_tabs",
                "parameters": {"urls_to_open": ["https://www.example.com"]},
            }
        ],
    )
    assert v2.classify_evaluator(web).label == "W"
    local = cfg(
        {"func": "f"}, config=[{"type": "open", "parameters": {"url": "http://localhost:8080"}}]
    )
    assert v2.classify_evaluator(local).label == "O"


# --------------------------------------------------------------------------- #
# Rule (d): stratified exact test
# --------------------------------------------------------------------------- #


def brute_force_stratified_p(strata: list[tuple[int, int, int, int]]) -> float:
    """Enumerate every per-stratum hypergeometric outcome (reference for the test)."""
    supports = []
    for _, n, k, n_l in strata:
        dist = stats.hypergeom(n, k, n_l)
        supports.append([(a, dist.pmf(a)) for a in range(0, min(k, n_l) + 1)])
    observed = sum(a for a, *_ in strata)
    total = 0.0
    for combo in itertools.product(*supports):
        if sum(a for a, _ in combo) >= observed:
            total += math.prod(p for _, p in combo)
    return total


@pytest.mark.parametrize(
    "strata",
    [
        [(5, 48, 7, 15), (3, 294, 16, 20)],
        [(0, 48, 7, 10), (0, 294, 16, 0)],
        [(7, 48, 7, 7), (0, 294, 16, 40)],
        [(2, 30, 4, 10)],
    ],
)
def test_stratified_exact_p_matches_enumeration(strata) -> None:
    assert v2.stratified_exact_p(strata) == pytest.approx(brute_force_stratified_p(strata))


def test_single_stratum_equals_fisher_one_sided() -> None:
    a, n, k, n_l = 4, 60, 6, 12
    table = [[a, n_l - a], [k - a, n - n_l - (k - a)]]
    assert v2.stratified_exact_p([(a, n, k, n_l)]) == pytest.approx(v2.fisher_one_sided(table))


def decide(rule_d_result, abc, **kwargs):
    """v2_decisions for a receipt that met every run condition."""
    return v2.v2_decisions(rule_d_result, abc, run_label=v2.CONFIRMATORY_LABEL, **kwargs)


def make_split(web_n=48, web_r1=7, off_n=294, off_r1=16, off_r2=9):
    """Clean set shaped like the known URL split: 7-0 among web tasks, 16-9 offline."""
    clean, web, s1, s2 = [], {}, {}, {}
    for stratum, n, r1, r2 in (("w", web_n, web_r1, 0), ("o", off_n, off_r1, off_r2)):
        for i in range(n):
            t = f"{stratum}{i}"
            clean.append(t)
            web[t] = stratum == "w"
            s1[t] = 0.0 if r1 <= i < r1 + r2 else 1.0
            s2[t] = 0.0 if i < r1 else 1.0
    return clean, web, s1, s2


def test_rule_d_is_not_driven_by_the_known_url_split() -> None:
    clean, web, s1, s2 = make_split()
    # L = every web task: the unstratified test just re-reads the known split.
    classes = {t: ("L" if web[t] else "O") for t in clean}
    result = v2.rule_d(classes, s1, s2, clean, web)
    assert result["strata"]["web"] == {
        "tasks": 48,
        "L": 48,
        "run1_only": 7,
        "run1_only_in_L": 7,
        "run2_only": 0,
        "run2_only_in_L": 0,
    }
    assert result["net_flips_all"] == 14 and result["share_of_net_in_L"] == 0.5
    assert result["unstratified_fisher_one_sided_p_descriptive"] < 0.04
    assert result["stratified_exact_one_sided_p"] == pytest.approx(1.0)
    assert v2.rule_d_decision(result) == "not attributable to checker time-dependence"


def test_rule_d_fires_on_enrichment_within_strata() -> None:
    clean, web, s1, s2 = make_split()
    # L holds the 7 web run1-only tasks plus 8 other web tasks, and 2 offline tasks.
    l_tasks = {f"w{i}" for i in range(15)} | {"o0", "o100"}
    classes = {t: ("L" if t in l_tasks else ("W" if web[t] else "O")) for t in clean}
    result = v2.rule_d(classes, s1, s2, clean, web)
    assert result["net_flips_L"] == 8 and result["share_of_net_in_L"] == pytest.approx(8 / 14)
    assert result["stratified_exact_one_sided_p"] < v2.ALPHA_D
    assert v2.rule_d_decision(result) == "checker-side time-drift candidate"
    assert result["by_class"]["L"] == {"tasks": 17, "run1_only": 8, "run2_only": 0}


def test_rule_d_decision_does_not_depend_on_rule_a() -> None:
    """Regression (review finding 2): (d) must not be rescued or sunk by (a)."""
    d = {"stratified_exact_one_sided_p": 0.03, "share_of_net_in_L": 0.6}
    without_a = decide(d, None)
    strong_a = decide(d, abc_stub(wilcoxon_p=1e-9, coverage_ok=True))
    limited_a = decide(d, abc_stub(wilcoxon_p=1e-9, coverage_ok=False))
    assert without_a["rule_d"] == strong_a["rule_d"] == limited_a["rule_d"]
    assert without_a["rule_d"] == "checker-side time-drift candidate"  # 0.03 < ALPHA_D
    assert limited_a["rule_a"] == "descriptive only (coverage < 95%)"
    assert limited_a["rule_b"] == "descriptive only (coverage < 95%)"
    assert without_a["rule_a"].startswith("NOT RUN")
    assert "p_holm" not in strong_a
    weak = decide({"stratified_exact_one_sided_p": 0.045, "share_of_net_in_L": 1.0}, None)
    assert weak["rule_d"] == "not attributable to checker time-dependence"


@pytest.mark.parametrize(
    ("p", "share", "label"),
    [
        (0.01, 0.5, "checker-side time-drift candidate"),
        (0.01, 0.43, "checker-side enrichment, minority of the gap"),
        (0.01, None, "checker-side enrichment, minority of the gap"),
        (0.04, 1.0, "not attributable to checker time-dependence"),
    ],
)
def test_rule_d_labels(p, share, label) -> None:
    assert v2.rule_d_decision({"stratified_exact_one_sided_p": p, "share_of_net_in_L": share}) == (
        label
    )


def test_narrow_l_sensitivity_is_reported() -> None:
    clean, web, s1, s2 = make_split()
    l_tasks = {f"w{i}" for i in range(15)} | {"o0", "o100"}
    broad = {t: ("L" if t in l_tasks else "O") for t in clean}
    narrow = {t: ("L" if t in {"o0"} else "not L") for t in clean}
    out = decide(
        v2.rule_d(broad, s1, s2, clean, web),
        None,
        rule_d_narrow=v2.rule_d(narrow, s1, s2, clean, web),
    )
    assert out["rule_d"] == "checker-side time-drift candidate"
    assert out["rule_d_narrow_L_sensitivity"] == "not attributable to checker time-dependence"
    assert out["rule_d_robust_to_L_definition"] is False


def abc_stub(*, wilcoxon_p: float, coverage_ok: bool, mean_log: float = 0.3) -> dict:
    labelled = {"verdict": "unexplained"}
    return {
        "rule_c_coverage": {"coverage_ok": coverage_ok},
        "rule_a_steps": {"wilcoxon_p": wilcoxon_p, "mean_log_ratio_run1_over_run2": mean_log},
        "rule_b_primary": labelled,
        "rule_b_sensitivity_all_criteria": labelled,
        "rule_b_sensitivity_step_cap_first": labelled,
    }


def test_power_rule_d_is_exact_and_sized() -> None:
    strata = {
        "web": {"tasks": 48, "run1_only": 7, "run2_only": 0},
        "offline": {"tasks": 294, "run1_only": 16, "run2_only": 9},
    }
    rows = v2.power_rule_d(strata, l_tasks=((20, 0), (0, 40)), odds_ratios=(1.0, 5.0, 30.0))
    by = {(r["L_tasks_web"], r["L_tasks_offline"], r["odds_ratio"]): r for r in rows}
    for scenario in ((20, 0), (0, 40)):
        assert by[(*scenario, 1.0)]["power_test_alone"] <= v2.ALPHA_D  # exact size
        assert by[(*scenario, 1.0)]["power"] <= by[(*scenario, 5.0)]["power"]
        assert by[(*scenario, 5.0)]["power"] <= by[(*scenario, 30.0)]["power"]
        for psi in (1.0, 5.0, 30.0):
            assert by[(*scenario, psi)]["power"] <= by[(*scenario, psi)]["power_test_alone"]
    # Inside the web stratum the share bar needs all 7 web run1-only tasks in L.
    p_all_seven = stats.nchypergeom_fisher(48, 7, 20, 30.0).pmf(7)
    assert by[(20, 0, 30.0)]["power"] <= p_all_seven + 1e-4  # power is rounded to 4 places


# --------------------------------------------------------------------------- #
# Rules (a)-(c): tarball features
# --------------------------------------------------------------------------- #

TRAJ_A = "11111111-2222-4333-8444-555555555555"
TRAJ_B = "66666666-7777-4888-8999-aaaaaaaaaaaa"


def _gz(data: bytes) -> bytes:
    return gzip.compress(data, mtime=0)


def make_tarball(path: Path) -> None:
    def actions(n: int, final: str, note: str = "") -> bytes:
        entries = []
        for i in range(n):
            entries.append({"image": f"images/{i:04d}.png"})
            tool = final if i == n - 1 else "click_desktop"
            entries.append(
                {"reasoning": "r", "thought": "t", "note": note, "action": {"tool_name": tool}}
            )
        return json.dumps(entries).encode()

    members = {
        f"fsx/person/run/trajectories_x/{TRAJ_A}/actions.json.gz": _gz(actions(4, "answer")),
        f"fsx/person/run/trajectories_x/{TRAJ_B}/actions.json.gz": _gz(
            actions(3, "answer", note="The page shows unusual traffic from your network")
        ),
        "fsx/person/run/README.txt": b"ignore me",
    }
    for i in range(4):
        members[f"fsx/person/run/trajectories_x/{TRAJ_A}/images/{i:04d}.png.gz"] = _gz(b"same")
    for i in range(3):
        members[f"fsx/person/run/trajectories_x/{TRAJ_B}/images/{i:04d}.png.gz"] = _gz(bytes([i]))
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def test_tarball_scan_keeps_ids_and_numbers_only(tmp_path: Path) -> None:
    tar = tmp_path / "t.tar.gz"
    make_tarball(tar)
    features = v2.scan_trajectory_tarball(tar)
    assert set(features) == {TRAJ_A, TRAJ_B}
    a, b = features[TRAJ_A], features[TRAJ_B]
    assert (a.steps, a.final_tool, a.max_identical_run()) == (4, "answer", 4)
    assert (b.steps, b.max_identical_run(), b.env_text_hits) == (3, 1, {"unusual_traffic": 3})
    public = json.dumps({k: f.public() for k, f in features.items()})
    assert "fsx" not in public and "person" not in public and "trajectories_x" not in public
    assert a.compressed_offset is not None and 0 < a.compressed_offset <= tar.stat().st_size
    rebuilt = v2.TrajectoryFeatures.from_public(json.loads(public)[TRAJ_A])
    assert rebuilt.max_identical_run() == 4 and rebuilt.steps == 4


def test_screenshot_order_falls_back_to_image_index() -> None:
    features = v2.TrajectoryFeatures("x", parsed=True)
    features.image_digests = {2: "a", 0: "b", 1: "a", 3: "a"}
    assert features.max_identical_run() == 3  # indices 1, 2, 3 in ascending order
    features.image_refs = [0, 1, 0, 2, 3]  # the order actions.json references them
    assert features.max_identical_run() == 2


def feat(steps: int, **kwargs) -> v2.TrajectoryFeatures:
    return v2.TrajectoryFeatures(
        "x", steps=steps, parsed=True, identical_run=kwargs.pop("run", 1), **kwargs
    )


OK_STATUS = {"agp_message": "Completed (trajectory=x)", "agp_actions": "['DONE']"}


def test_failure_signature_order() -> None:
    sig = v2.failure_signature
    assert sig(None, None, OK_STATUS) == "unclassifiable"
    assert sig(feat(10, env_text_hits={"captcha": 1}), feat(10), OK_STATUS) == "environment"
    assert sig(feat(10, tool_error_entries=1), feat(10), OK_STATUS) == "environment"
    assert sig(feat(100), feat(10), OK_STATUS) == "step_cap"
    assert sig(feat(5), feat(10), OK_STATUS) == "premature_answer"
    infeasible = {"agp_message": "Infeasible (x)", "agp_actions": "['FAIL']"}
    assert sig(feat(9), feat(10), infeasible) == "declared_infeasible"
    assert sig(feat(9), feat(10), OK_STATUS) == "other"
    # Screenshots count only when the criterion is passed in (sensitivity).
    assert sig(feat(10, run=3), feat(10), OK_STATUS) == "other"
    assert sig(feat(10, run=3), feat(10), OK_STATUS, v2.ENV_CRITERIA) == "environment"


def test_environment_signature_is_checked_before_the_step_cap() -> None:
    """Regression (review finding 5): a capped episode with an environment
    signature is an environment failure; the plan's order is a sensitivity."""
    capped_blocked = feat(100, env_text_hits={"access_denied": 2})
    assert v2.failure_signature(capped_blocked, feat(30), OK_STATUS) == "environment"
    assert (
        v2.failure_signature(capped_blocked, feat(30), OK_STATUS, step_cap_first=True) == "step_cap"
    )


def episode_world(n_tasks: int = 40):
    tasks = [f"t{i}" for i in range(n_tasks)]
    s1 = {t: 1.0 for t in tasks}
    s2 = {t: 1.0 for t in tasks}
    status1 = {t: {"trajectory_id": f"a{t}", "agp_message": "Completed"} for t in tasks}
    status2 = {t: {"trajectory_id": f"b{t}", "agp_message": "Completed"} for t in tasks}
    features = {}
    for t in tasks:
        features[f"a{t}"] = v2.TrajectoryFeatures(f"a{t}", steps=20, parsed=True, identical_run=1)
        features[f"b{t}"] = v2.TrajectoryFeatures(f"b{t}", steps=20, parsed=True, identical_run=1)
    return tasks, s1, s2, status1, status2, features


def h_world(tasks: list[str], ref_failures: dict[str, dict[str, v2.TrajectoryFeatures]]):
    """Three H runs that pass everything except the given unique failures."""
    tags = ("h1", "h2", "h3")
    rewards = {tag: {t: 1.0 for t in tasks} for tag in tags}
    features = {tag: {t: feat(20) for t in tasks} for tag in tags}
    for tag, failures in ref_failures.items():
        for t, f in failures.items():
            rewards[tag][t] = 0.0
            features[tag][t] = f
    return rewards, features


def test_rule_b_needs_an_excess_over_the_h_rerun_reference() -> None:
    """Regression (review finding 1): a composition that exchangeable reruns
    also show gets no session-variation label, however large its share."""
    tasks, s1, s2, status1, status2, features = episode_world()
    run2_failures = tasks[:10]
    for t in run2_failures:
        s2[t] = 0.0
    for t in run2_failures[:5]:  # 5 of 10 step-capped, as in H run 072452
        features[f"b{t}"].steps = 100
    # Reference: the H runs' unique failures are half step-capped too.
    ref = {
        "h1": {t: feat(100) for t in tasks[20:25]} | {t: feat(20) for t in tasks[25:30]},
        "h2": {t: feat(100) for t in tasks[30:33]} | {t: feat(20) for t in tasks[33:36]},
    }
    h_rewards, h_features = h_world(tasks, ref)
    for t in tasks[20:36]:  # those tasks still pass in both maintainer runs
        assert s1[t] == s2[t] == 1.0
    out = v2.rules_abc(
        features=features,
        status1=status1,
        status2=status2,
        s1=s1,
        s2=s2,
        clean=tasks,
        h_rewards=h_rewards,
        h_features=h_features,
    )
    primary = out["rule_b_primary"]
    assert primary["run2_unique_failures"]["agent_side_share"] == 0.5
    assert primary["h_reference"]["pooled"]["tasks"] == 16
    assert primary["h_reference"]["pooled"]["agent_side"] == 8
    assert primary["verdict"] == "unexplained"
    # The same run against a reference with no capped failures does get the label.
    clean_ref = {
        "h1": {t: feat(20) for t in tasks[20:30]},
        "h2": {t: feat(20) for t in tasks[30:36]},
    }
    h_rewards, h_features = h_world(tasks, clean_ref)
    for t in run2_failures[5:8]:
        features[f"b{t}"].steps = 100
    out = v2.rules_abc(
        features=features,
        status1=status1,
        status2=status2,
        s1=s1,
        s2=s2,
        clean=tasks,
        h_rewards=h_rewards,
        h_features=h_features,
    )
    assert out["rule_b_primary"]["verdict"] == "agent-side session variation"


def test_rules_abc_coverage_unique_failures_and_decisions() -> None:
    tasks, s1, s2, status1, status2, features = episode_world(40)
    for t in tasks[:4]:
        s2[t] = 0.0  # run2-unique failures
    for t in tasks:
        features[f"b{t}"].steps = 30
    for t in tasks[:3]:
        features[f"b{t}"].env_text_hits = {"captcha": 1}  # environment signature
    reference = {
        "h1": {t: feat(20) for t in tasks[20:28]},
        "h2": {t: feat(20) for t in tasks[28:36]},
    }
    h_rewards, h_features = h_world(tasks, reference)
    out = v2.rules_abc(
        features=features,
        status1=status1,
        status2=status2,
        s1=s1,
        s2=s2,
        clean=tasks,
        h_rewards=h_rewards,
        h_features=h_features,
    )
    assert out["rule_c_coverage"]["fraction"] == 1.0
    primary = out["rule_b_primary"]
    assert primary["run2_unique_failures"]["tasks"] == 4
    assert primary["run2_unique_failures"]["environment"] == 3
    assert primary["verdict"] == "R1-retro: infrastructure"
    assert out["rule_a_steps"]["geometric_mean_ratio_run1_over_run2"] == pytest.approx(20 / 30)
    decisions = decide({"stratified_exact_one_sided_p": 0.5, "share_of_net_in_L": 0.0}, out)
    assert decisions["rule_a"] == "agent-behaviour shift"
    assert decisions["rule_b"] == "R1-retro: infrastructure"
    assert decisions["rule_b_sensitivity_step_cap_first"] == "R1-retro: infrastructure"

    for t in tasks[5:10]:  # 75 of 80 episodes join
        del features[f"b{t}"]
    partial = v2.rules_abc(
        features=features,
        status1=status1,
        status2=status2,
        s1=s1,
        s2=s2,
        clean=tasks,
        h_rewards=h_rewards,
        h_features=h_features,
    )
    assert partial["rule_c_coverage"]["coverage_ok"] is False
    assert decide({"stratified_exact_one_sided_p": 0.5, "share_of_net_in_L": 0.0}, partial)[
        "rule_b"
    ].startswith("descriptive only")


def test_specificity_guard_drops_a_criterion_that_fires_on_passing_episodes() -> None:
    tasks, s1, s2, status1, status2, features = episode_world(20)
    for t in tasks[:4]:
        s2[t] = 0.0
    for f in features.values():  # every episode mentions a rate limit
        f.env_text_hits = {"rate_limit": 1}
        f.identical_run = 3
    features["bt0"].tool_error_entries = 1
    h_rewards, h_features = h_world(tasks, {"h1": {"t10": feat(20)}})
    out = v2.rules_abc(
        features=features,
        status1=status1,
        status2=status2,
        s1=s1,
        s2=s2,
        clean=tasks,
        h_rewards=h_rewards,
        h_features=h_features,
    )
    guard = out["rule_b_specificity"]
    assert guard["share_firing"]["text"] == 1.0 and guard["share_firing"]["screenshots"] == 1.0
    assert guard["criteria_in_force"] == ["tool_error"]
    assert out["rule_b_primary"]["run2_unique_failures"]["classes"] == {
        "environment": 1,
        "other": 3,
    }
    assert out["rule_b_sensitivity_all_criteria"]["run2_unique_failures"]["environment"] == 4


@pytest.mark.parametrize("factor", [1.11, 1 / 1.11, 1.09, 1 / 1.09])
def test_rule_a_effect_size_is_symmetric_in_log_steps(factor: float) -> None:
    base = np.array([float(10 + (i % 9)) for i in range(300)])
    result = v2.step_shift(base * factor, base)
    assert abs(result["mean_log_ratio_run1_over_run2"]) == pytest.approx(abs(math.log(factor)))
    assert v2.rule_a_decision(result) is (abs(math.log(factor)) > math.log(1.10))


def test_rule_a_sees_a_shift_confined_to_a_subset_of_tasks() -> None:
    """Regression (review finding 4): with many tied pairs the median ratio stays
    at 1.0 under a large shift on 30% of tasks; the registered effect size does not."""
    rng = np.random.default_rng(0)
    run2 = rng.integers(5, 40, size=342).astype(float)
    run1 = run2.copy()
    subset = rng.random(342) < 0.3
    run1[subset] = np.round(run1[subset] * 1.5)
    result = v2.step_shift(run1, run2)
    assert result["median_ratio_run1_over_run2_descriptive"] == 1.0
    assert result["wilcoxon_p"] < 1e-6
    assert v2.rule_a_decision(result)


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #


def stored_fixture():
    payload = bytes(range(256)) * 1000
    outer = zip_bytes({"pkg/t.tar.gz": payload, "pkg/README": b"r"}, stored={"pkg/t.tar.gz"})
    source = BytesSource(outer)
    (member,) = remote_zip.select(remote_zip.list_members(source), ["pkg/t.tar.gz"])
    return payload, source, member, hashlib.sha256(payload).hexdigest()


def test_download_stored_member_resumes_and_verifies(tmp_path: Path) -> None:
    payload, source, member, digest = stored_fixture()
    dest = tmp_path / "t.tar.gz"
    (tmp_path / "t.tar.gz.part").write_bytes(payload[:10_000])  # an interrupted earlier attempt
    info = v2.download_stored_member(source, member, dest, expected_sha256=digest, chunk=50_000)
    assert dest.read_bytes() == payload and info["sha256"] == digest
    assert info["resumed_from_bytes"] == 10_000 and info["reused_existing_file"] is False
    assert source.stats.bytes < len(payload) + 1000  # the first 10,000 bytes were not refetched

    bad = tmp_path / "bad.tar.gz"
    with pytest.raises(remote_zip.ZipIntegrityError):
        v2.download_stored_member(source, member, bad, expected_sha256="0" * 64)
    assert not bad.exists()


def test_a_corrupt_partial_download_is_discarded_so_a_retry_succeeds(tmp_path: Path) -> None:
    """Regression (review finding 7): a garbage .part used to fail every retry."""
    payload, source, member, digest = stored_fixture()
    dest = tmp_path / "t.tar.gz"
    part = tmp_path / "t.tar.gz.part"
    part.write_bytes(b"\xff" * 10_000)
    with pytest.raises(remote_zip.ZipIntegrityError):
        v2.download_stored_member(source, member, dest, expected_sha256=digest)
    assert not part.exists() and not dest.exists()
    info = v2.download_stored_member(source, member, dest, expected_sha256=digest)
    assert info["sha256"] == digest and dest.read_bytes() == payload


def test_an_existing_destination_is_reverified(tmp_path: Path) -> None:
    payload, source, member, digest = stored_fixture()
    dest = tmp_path / "t.tar.gz"
    dest.write_bytes(payload)
    before = source.stats.bytes
    info = v2.download_stored_member(source, member, dest, expected_sha256=digest)
    assert info == {
        "size": len(payload),
        "crc32": f"{member.crc:08x}",
        "sha256": digest,
        "reused_existing_file": True,
    }
    assert source.stats.bytes == before  # nothing fetched
    dest.write_bytes(payload[:-1] + b"\x00")
    with pytest.raises(remote_zip.ZipIntegrityError):
        v2.download_stored_member(source, member, dest, expected_sha256=digest)
    assert not dest.exists()


# --------------------------------------------------------------------------- #
# Design power
# --------------------------------------------------------------------------- #


def test_power_rule_a_reports_subset_shifts_and_the_superseded_gate() -> None:
    pairs = [(10 + (i % 7), 10 + (i % 7)) for i in range(200)] + [
        (10 + (i % 5), 11 + (i % 3)) for i in range(200)
    ]
    rows = v2.power_rule_a(pairs, n=300, scenarios=((1.0, 1.0), (0.3, 1.5)), sims=20, seeds=(42,))
    null, subset = rows
    assert null["power_mean"] <= 0.1
    assert subset["power_mean"] > 0.5
    assert subset["power_mean_superseded_median_gate"] < subset["power_mean"]


def test_rule_b_thresholds() -> None:
    reference = {"tasks": 33, "environment": 2, "agent_side": 11}
    thresholds = v2.rule_b_thresholds(14, reference)
    env, agent = thresholds["environment"], thresholds["agent_side"]
    assert env == 7  # the share bar binds: Fisher is already small at 7/14 vs 2/33
    assert agent > 7  # 7/14 vs 11/33 is not an excess over the reference
    for key, k in thresholds.items():
        p = v2.fisher_one_sided([[k, 14 - k], [reference[key], 33 - reference[key]]])
        assert p < v2.ALPHA_B
        p_below = v2.fisher_one_sided([[k - 1, 15 - k], [reference[key], 33 - reference[key]]])
        assert p_below >= v2.ALPHA_B or (k - 1) / 14 < v2.SHARE_BAR
    assert v2.rule_b_thresholds(0, reference) == {"environment": None, "agent_side": None}


# --------------------------------------------------------------------------- #
# Pre-freeze audit (2026-10-07): rule-code consistency and owner conditions
# --------------------------------------------------------------------------- #


def _parsed(entries: list) -> v2.TrajectoryFeatures:
    features = v2.TrajectoryFeatures("x")
    v2.parse_actions(features, entries)
    return features


@pytest.mark.parametrize(
    "entry",
    [
        {"action": {"tool_name": "click"}, "error": False},
        {"action": {"tool_name": "click"}, "error": 0},
        {"action": {"tool_name": "click"}, "error": None},
        {"action": {"tool_name": "click"}, "error": ""},
        {"action": {"tool_name": "click"}, "exception": []},
        {"action": {"tool_name": "click"}, "traceback": {}},
        {"action": {"tool_name": "click"}, "Error": "boom"},  # key names are case-sensitive
        {"action": {"tool_name": "click", "result": {"TOOL_ERROR": "x"}}},
    ],
)
def test_tool_error_needs_an_exact_key_with_a_non_empty_value(entry: dict) -> None:
    """Audit finding: {'error': False}, {'error': 0} and 'Error' used to count."""
    assert _parsed([entry]).tool_error_entries == 0


@pytest.mark.parametrize(
    "entry",
    [
        {"action": {"tool_name": "click"}, "error": "boom"},
        {"action": {"tool_name": "click"}, "error": True},
        {"action": {"tool_name": "click", "result": {"traceback": ["line 1"]}}},
        {"action": {"tool_name": "click"}, "tool_error": {"code": 1}},
        {"action": {"tool_name": "click"}, "exception": 3},
    ],
)
def test_tool_error_fires_on_a_non_empty_value_at_any_depth(entry: dict) -> None:
    assert _parsed([entry]).tool_error_entries == 1


def test_text_patterns_do_not_match_across_fields() -> None:
    """Audit finding: the three text fields were joined, so 'connection' in
    reasoning plus 'failed to open' in thought fired the connection pattern."""
    split = _parsed([{"reasoning": "connection", "thought": "failed to open", "action": {}}])
    assert split.env_text_hits == {}
    one_field = _parsed([{"note": "Connection refused by the host", "action": {}}])
    assert one_field.env_text_hits == {"connection": 1}
    both = _parsed([{"reasoning": "captcha shown", "thought": "a captcha again", "action": {}}])
    assert both.env_text_hits == {"captcha": 1}  # counted once per entry


def test_a_checker_side_label_not_robust_to_narrow_l_is_exploratory() -> None:
    """D15 condition: a checker-side label that the narrow-L sensitivity does
    not reproduce is reported as exploratory."""
    clean, web, s1, s2 = make_split()
    l_tasks = {f"w{i}" for i in range(15)} | {"o0", "o100"}
    broad = v2.rule_d({t: ("L" if t in l_tasks else "O") for t in clean}, s1, s2, clean, web)
    narrow_none = v2.rule_d({t: "not L" for t in clean}, s1, s2, clean, web)
    out = decide(broad, None, rule_d_narrow=narrow_none)
    assert out["rule_d"] == "checker-side time-drift candidate"
    assert out["rule_d_robust_to_L_definition"] is False
    assert out["rule_d_evidence"].startswith("EXPLORATORY")
    robust = decide(broad, None, rule_d_narrow=broad)
    assert robust["rule_d_evidence"] == "CONFIRMATORY"
    # A null primary is not a checker-side label: it stays confirmatory even if
    # the sensitivity differs (it is still reported as not robust).
    null = decide(narrow_none, None, rule_d_narrow=broad)
    assert null["rule_d"] == "not attributable to checker time-dependence"
    assert null["rule_d_robust_to_L_definition"] is False
    assert null["rule_d_evidence"] == "CONFIRMATORY"
    missing = decide(broad, None)
    assert missing["rule_d_evidence"].startswith("EXPLORATORY")


def test_rule_d_evidence_is_never_confirmatory_in_a_non_confirmatory_run() -> None:
    """Re-audit (2026-10-07): a NON-CONFIRMATORY receipt said "CONFIRMATORY"
    for any robust or non-checker-side rule (d) label."""
    clean, web, s1, s2 = make_split()
    l_tasks = {f"w{i}" for i in range(15)} | {"o0", "o100"}
    broad = v2.rule_d({t: ("L" if t in l_tasks else "O") for t in clean}, s1, s2, clean, web)
    narrow_none = v2.rule_d({t: "not L" for t in clean}, s1, s2, clean, web)
    for label in ("v2 NON-CONFIRMATORY", "DESIGN", "POST-HOC", "", "v2 confirmatory"):
        for primary, sensitivity in (
            (broad, broad),  # robust checker-side label
            (narrow_none, broad),  # null primary
            (broad, narrow_none),  # checker-side label, not robust
            (broad, None),  # no sensitivity
        ):
            out = v2.v2_decisions(primary, None, run_label=label, rule_d_narrow=sensitivity)
            assert out["rule_d_evidence"] == "NON-CONFIRMATORY run", (label, out["rule_d"])
    robust = v2.v2_decisions(broad, None, run_label=v2.CONFIRMATORY_LABEL, rule_d_narrow=broad)
    assert robust["rule_d_evidence"] == "CONFIRMATORY"
    with pytest.raises(TypeError):
        v2.v2_decisions(broad, None, rule_d_narrow=broad)  # the label is required


def test_every_rule_d_output_carries_the_blinding_note_and_attainable_share() -> None:
    clean, web, s1, s2 = make_split()
    l_web_only = {f"w{i}" for i in range(20)}
    result = v2.rule_d({t: ("L" if t in l_web_only else "O") for t in clean}, s1, s2, clean, web)
    assert result["blinding"] == v2.RULE_D_BLINDING_NOTE
    assert "self-attested" in v2.RULE_D_BLINDING_NOTE
    # 20 L tasks inside the URL stratum hold at most its 7 run1-only tasks: share 7/14.
    assert result["max_attainable_share_of_net_in_L"] == pytest.approx(0.5)
    decisions = decide(result, None, rule_d_narrow=result)
    assert decisions["rule_d_blinding"] == v2.RULE_D_BLINDING_NOTE


def test_max_attainable_share_counts_forced_run2_only_tasks() -> None:
    clean, web, s1, s2 = make_split(off_n=30, off_r1=16, off_r2=9)
    every = v2.rule_d({t: "L" for t in clean}, s1, s2, clean, web)
    assert every["max_attainable_share_of_net_in_L"] == pytest.approx(1.0)  # net 14 of 14
    offline_only = v2.rule_d({t: ("O" if web[t] else "L") for t in clean}, s1, s2, clean, web)
    assert offline_only["max_attainable_share_of_net_in_L"] == pytest.approx(7 / 14)


def test_the_nominal_family_wise_error_rate_is_stated() -> None:
    """D15 condition: the nominal family-wise rate over (a), (b) and (d) is 0.10."""
    out = decide({"stratified_exact_one_sided_p": 0.5, "share_of_net_in_L": 0.0}, None)
    assert out["error_rates"]["nominal_family_wise_rate_a_b_d"] == pytest.approx(0.10)
    bonferroni_bound = v2.ALPHA_D + v2.ALPHA_A + 2 * v2.ALPHA_B
    assert bonferroni_bound == pytest.approx(v2.NOMINAL_FAMILY_WISE_RATE)


def _outcome_world(n_concordant: int = 300, n_run1_only: int = 30):
    """Concordant tasks with identical step counts; run1-only tasks whose run2
    (failing) trajectory hits the step cap, as failing episodes often do."""
    tasks = [f"t{i}" for i in range(n_concordant + n_run1_only)]
    s1 = {t: 1.0 for t in tasks}
    s2 = {t: 1.0 for t in tasks}
    status1 = {t: {"trajectory_id": f"a{t}"} for t in tasks}
    status2 = {t: {"trajectory_id": f"b{t}"} for t in tasks}
    features = {}
    for i, t in enumerate(tasks):
        steps = 10 + i % 9
        run2_steps = steps
        if i >= n_concordant:
            s2[t] = 0.0
            run2_steps = 100
        features[f"a{t}"] = v2.TrajectoryFeatures(f"a{t}", steps=steps, parsed=True)
        features[f"b{t}"] = v2.TrajectoryFeatures(f"b{t}", steps=run2_steps, parsed=True)
    return tasks, s1, s2, status1, status2, features


def test_rule_a_concordant_sensitivity_removes_the_known_outcome_asymmetry() -> None:
    """Audit blocking defect 3: failing episodes are longer, so known run1-only
    discordance alone moves m; the concordant-task sensitivity does not see it."""
    tasks, s1, s2, status1, status2, features = _outcome_world()
    h_rewards, h_features = h_world(tasks, {})
    out = v2.rules_abc(
        features=features,
        status1=status1,
        status2=status2,
        s1=s1,
        s2=s2,
        clean=tasks,
        h_rewards=h_rewards,
        h_features=h_features,
    )
    concordant = out["rule_a_steps_concordant_tasks"]
    assert concordant["n_pairs"] == 300 and concordant["tied_pairs"] == 300
    assert out["rule_a_steps"]["n_pairs"] == 330
    decisions = decide({"stratified_exact_one_sided_p": 0.5, "share_of_net_in_L": 0.0}, out)
    assert decisions["rule_a"] == "agent-behaviour shift"
    assert decisions["rule_a_sensitivity_concordant_tasks"] == "no agent-behaviour shift"
    assert decisions["rule_a_robust_to_concordant_tasks"] is False


def test_all_criteria_sensitivity_is_not_run_when_no_screenshot_matched() -> None:
    """Audit note: if the tarball's image layout differs from the registered
    one, the screenshot sensitivity must not silently equal the primary."""
    tasks, s1, s2, status1, status2, features = episode_world(20)
    for t in tasks[:4]:
        s2[t] = 0.0
    h_rewards, h_features = h_world(tasks, {"h1": {"t10": feat(20)}})
    kwargs = dict(
        status1=status1,
        status2=status2,
        s1=s1,
        s2=s2,
        clean=tasks,
        h_rewards=h_rewards,
        h_features=h_features,
    )
    blind = v2.rules_abc(features=features, **kwargs)
    assert blind["rule_b_screenshots"]["joined_episodes_with_screenshots"] == 0
    assert blind["rule_b_sensitivity_all_criteria"]["verdict"].startswith("NOT RUN")
    for f in features.values():
        f.image_count = 5
    seen = v2.rules_abc(features=features, **kwargs)
    assert seen["rule_b_screenshots"]["joined_episodes_with_screenshots"] == 40
    assert not seen["rule_b_sensitivity_all_criteria"]["verdict"].startswith("NOT RUN")


def test_rule_b_class_order_robustness_is_reported() -> None:
    tasks, s1, s2, status1, status2, features = episode_world(40)
    for t in tasks[:4]:
        s2[t] = 0.0
        features[f"b{t}"].steps = 100
        features[f"b{t}"].env_text_hits = {"captcha": 1}
    h_rewards, h_features = h_world(tasks, {"h1": {t: feat(20) for t in tasks[20:30]}})
    out = v2.rules_abc(
        features=features,
        status1=status1,
        status2=status2,
        s1=s1,
        s2=s2,
        clean=tasks,
        h_rewards=h_rewards,
        h_features=h_features,
    )
    decisions = decide({"stratified_exact_one_sided_p": 0.5, "share_of_net_in_L": 0.0}, out)
    assert decisions["rule_b"] == "R1-retro: infrastructure"
    assert decisions["rule_b_sensitivity_step_cap_first"] == "agent-side session variation"
    assert decisions["rule_b_robust_to_class_order"] is False


def test_public_features_keep_the_image_count() -> None:
    features = v2.TrajectoryFeatures("x", steps=3, parsed=True)
    features.image_digests = {0: "a", 1: "b"}
    public = features.public()
    assert public["images"] == 2 and "image_count" not in public
    rebuilt = v2.TrajectoryFeatures.from_public(public)
    assert rebuilt.n_images() == 2 and rebuilt.public() == public


def test_tarball_scan_reports_its_member_layout(tmp_path: Path) -> None:
    tar = tmp_path / "t.tar.gz"
    make_tarball(tar)
    layout: dict = {}
    v2.scan_trajectory_tarball(tar, layout=layout)
    assert layout == {
        "file_members": 10,
        "actions_members": 2,
        "image_members": 7,
        "other_file_members": 1,
        "trajectories_with_actions": 2,
        "trajectories_with_images": 2,
    }


def test_tarball_literals_match_the_registration() -> None:
    flat = " ".join((ROOT_PREREG / "q2-holo3-rerun-audit-v2.md").read_text().split())
    assert f"{v2.TARBALL_SIZE:,} B" in flat
    assert f"CRC-32 `{v2.TARBALL_CRC32:08x}`" in flat
    assert f"SHA-256 `{v2.TARBALL_SHA256}`" in flat


ROOT_PREREG = Path(__file__).resolve().parents[1] / "program" / "preregistrations"


# ---- Design numbers added after the pre-freeze audit ---------------------- #


def test_outcome_pools_orient_discordant_pairs_by_outcome() -> None:
    steps = {"h1": {"a": 10, "b": 20, "c": 7}, "h2": {"a": 12, "b": 100, "c": 9}}
    rewards = {"h1": {"a": 1.0, "b": 1.0, "c": 0.0}, "h2": {"a": 1.0, "b": 0.0, "c": 0.0}}
    pools = v2.outcome_pools(steps, rewards)
    assert sorted(pools["both_pass"]) == [(10, 12), (12, 10)]
    assert sorted(pools["both_fail"]) == [(7, 9), (9, 7)]
    assert pools["run1_only"] == [(20, 100)]  # (passing steps, failing steps)
    assert pools["run2_only"] == [(100, 20)]


def test_power_rule_a_by_outcome_shows_the_offset_of_known_discordance() -> None:
    uneven = [(10 + i % 5, 11 + i % 3) for i in range(50)]
    pools = {
        "both_pass": [(10 + i % 7, 10 + i % 7) for i in range(50)]
        + uneven
        + [(b, a) for a, b in uneven],
        "both_fail": [(30 + i % 9, 30 + i % 9) for i in range(40)],
        "run1_only": [(12, 100), (11, 60), (14, 90), (13, 40)],
        "run2_only": [(100, 12), (60, 11), (90, 14), (40, 13)],
    }
    counts = {"both_pass": 260, "run1_only": 23, "run2_only": 9, "both_fail": 50}
    rows = v2.power_rule_a_by_outcome(
        pools, counts, scenarios=((1.0, 1.0), (1.0, 1.10), (1.0, 1 / 1.10)), sims=20, seeds=(42,)
    )
    null, longer, shorter = rows
    assert null["mean_m"] < -0.05  # run2 longer by construction of the known 23/9
    assert abs(null["mean_m_concordant_tasks"]) < 0.02
    assert longer["power_mean"] > shorter["power_mean"]  # direction-dependent
    assert null["power_mean_concordant_tasks"] <= 0.1


def test_size_of_rule_d_over_every_allocation_stays_below_alpha() -> None:
    strata = {
        "web": {"tasks": 48, "run1_only": 7, "run2_only": 0},
        "offline": {"tasks": 294, "run1_only": 16, "run2_only": 9},
    }
    out = v2.size_rule_d_all_allocations(strata, step=(4, 21))
    assert out["allocations"] == 13 * 15
    assert 0 < out["max_size"] < v2.ALPHA_D
    web_l, off_l = out["max_size_at"]
    tabled = v2.power_rule_d(strata, l_tasks=((web_l, off_l),), odds_ratios=(1.0,))
    assert tabled[0]["power_test_alone"] == pytest.approx(out["max_size"], abs=1e-6)


def test_power_rule_b_is_binomial_above_the_count_thresholds() -> None:
    rows = v2.power_rule_b(14, {"environment": 7, "agent_side": 10}, shares=(0.5, 0.7))
    by = {(r["class"], r["share"]): r["power"] for r in rows}
    assert by[("environment", 0.5)] == pytest.approx(stats.binom.sf(6, 14, 0.5))
    assert by[("agent_side", 0.7)] == pytest.approx(stats.binom.sf(9, 14, 0.7))
