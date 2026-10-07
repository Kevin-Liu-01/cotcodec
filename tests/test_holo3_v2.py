from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

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
    ("config", "label", "reason"),
    [
        (
            cfg({"func": "check", "expected": {"type": "rule_relativeTime", "rules": {}}}),
            "L",
            "getter:rule_relativeTime",
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
        ),
        (
            cfg({"func": ["a", "b"], "result": [{"type": "active_tab_info"}, {"type": "vm_file"}]}),
            "L",
            "getter:active_tab_info",
        ),
        (
            cfg({"func": "compare_time_in_speedtest_results", "result": {"type": "vm_file"}}),
            "L",
            "metric:compare_time_in_speedtest_results",
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
        ),
    ],
)
def test_live_or_clock_evaluators_are_class_l(config: dict, label: str, reason: str) -> None:
    result = v2.classify_evaluator(config)
    assert result.label == label
    assert reason in result.reasons


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


def test_rule_d_table_share_and_decision() -> None:
    clean = [f"t{i}" for i in range(100)]
    classes = {t: ("L" if i < 10 else ("W" if i < 30 else "O")) for i, t in enumerate(clean)}
    s1 = {t: 1.0 for t in clean}
    s2 = {t: 1.0 for t in clean}
    for i in range(8):  # eight run1-only passes, all in L
        s2[clean[i]] = 0.0
    s2[clean[50]] = 0.0  # one more run1-only pass in O
    s1[clean[60]] = 0.0  # one run2-only pass in O
    result = v2.rule_d(classes, s1, s2, clean)
    assert result["table_L_vs_rest_by_run1_only"] == [[8, 2], [1, 89]]
    assert result["net_flips_all"] == 8 and result["net_flips_L"] == 8
    assert result["share_of_net_in_L"] == 1.0
    assert result["fisher_one_sided_p"] < 1e-6
    decision = v2.v2_decisions(result, None)
    assert decision["rule_d"] == "checker-side time-drift candidate"
    assert decision["p_raw"]["a"] == 1.0  # (a) not run enters Holm with p = 1
    assert decision["p_holm"]["d"] == pytest.approx(2 * result["fisher_one_sided_p"])
    assert decision["rule_a"].startswith("NOT RUN")

    no_signal = v2.rule_d({t: "O" if t != clean[0] else "L" for t in clean}, s1, s2, clean)
    assert (
        v2.v2_decisions(no_signal, None)["rule_d"] == "not attributable to checker time-dependence"
    )


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
        f"fsx/person/run/trajectories_tianbao/{TRAJ_A}/actions.json.gz": _gz(actions(4, "answer")),
        f"fsx/person/run/trajectories_tianbao/{TRAJ_B}/actions.json.gz": _gz(
            actions(3, "answer", note="The page shows unusual traffic from your network")
        ),
        "fsx/person/run/README.txt": b"ignore me",
    }
    for i in range(4):
        members[f"fsx/person/run/trajectories_tianbao/{TRAJ_A}/images/{i:04d}.png.gz"] = _gz(
            b"same"
        )
    for i in range(3):
        members[f"fsx/person/run/trajectories_tianbao/{TRAJ_B}/images/{i:04d}.png.gz"] = _gz(
            bytes([i])
        )
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
    assert "fsx" not in public and "person" not in public
    assert a.compressed_offset is not None and 0 < a.compressed_offset <= tar.stat().st_size
    rebuilt = v2.TrajectoryFeatures.from_public(json.loads(public)[TRAJ_A])
    assert rebuilt.max_identical_run() == 4 and rebuilt.steps == 4


def test_failure_signature_order() -> None:
    def feat(steps: int, **kwargs) -> v2.TrajectoryFeatures:
        return v2.TrajectoryFeatures(
            "x", steps=steps, parsed=True, identical_run=kwargs.pop("run", 1), **kwargs
        )

    ok = {"agp_message": "Completed (trajectory=x)", "agp_actions": "['DONE']"}
    assert v2.failure_signature(None, None, ok) == "unclassifiable"
    assert (
        v2.failure_signature(feat(100, env_text_hits={"captcha": 1}), feat(10), ok) == "1_step_cap"
    )
    assert v2.failure_signature(feat(10, run=3), feat(10), ok) == "2_environment"
    assert v2.failure_signature(feat(10, tool_error_entries=1), feat(10), ok) == "2_environment"
    assert v2.failure_signature(feat(5), feat(10), ok) == "3_premature_answer"
    infeasible = {"agp_message": "Infeasible (x)", "agp_actions": "['FAIL']"}
    assert v2.failure_signature(feat(9), feat(10), infeasible) == "4_declared_infeasible"
    assert v2.failure_signature(feat(9), feat(10), ok) == "5_other"


def test_rules_abc_coverage_unique_failures_and_decisions() -> None:
    tasks = [f"t{i}" for i in range(20)]
    s1 = {t: 1.0 for t in tasks}
    s2 = {t: 1.0 for t in tasks}
    for t in tasks[:4]:
        s2[t] = 0.0  # run2-unique failures
    h = {tag: {t: 1.0 for t in tasks} for tag in ("h1", "h2", "h3")}
    status1 = {t: {"trajectory_id": f"a{t}", "agp_message": "Completed"} for t in tasks}
    status2 = {t: {"trajectory_id": f"b{t}", "agp_message": "Completed"} for t in tasks}
    features = {}
    for t in tasks:
        features[f"a{t}"] = v2.TrajectoryFeatures(f"a{t}", steps=20, parsed=True, identical_run=1)
        features[f"b{t}"] = v2.TrajectoryFeatures(f"b{t}", steps=30, parsed=True, identical_run=1)
    for t in tasks[:3]:
        features[f"b{t}"].identical_run = 5  # environment signature
    out = v2.rules_abc(
        features=features, status1=status1, status2=status2, s1=s1, s2=s2, clean=tasks, h_rewards=h
    )
    assert out["rule_c_coverage"]["fraction"] == 1.0
    assert out["rule_b_run2_unique_failures"]["tasks"] == 4
    assert out["rule_b_run2_unique_failures"]["verdict"] == "R1-retro: infrastructure"
    assert out["rule_a_steps"]["median_ratio_run1_over_run2"] == pytest.approx(20 / 30)
    decisions = v2.v2_decisions({"fisher_one_sided_p": 0.5, "share_of_net_in_L": 0.0}, out)
    assert decisions["rule_a"] == "agent-behaviour shift"
    assert decisions["rule_b"] == "R1-retro: infrastructure"

    del features["bt5"], features["bt6"], features["bt7"]  # 37 of 40 episodes join
    partial = v2.rules_abc(
        features=features, status1=status1, status2=status2, s1=s1, s2=s2, clean=tasks, h_rewards=h
    )
    assert partial["rule_c_coverage"]["coverage_ok"] is False
    assert v2.v2_decisions({"fisher_one_sided_p": 0.5, "share_of_net_in_L": 0.0}, partial)[
        "rule_b"
    ].startswith("descriptive only")


def test_download_stored_member_resumes_and_verifies(tmp_path: Path) -> None:
    payload = bytes(range(256)) * 1000
    outer = zip_bytes({"pkg/t.tar.gz": payload, "pkg/README": b"r"}, stored={"pkg/t.tar.gz"})
    source = BytesSource(outer)
    (member,) = remote_zip.select(remote_zip.list_members(source), ["pkg/t.tar.gz"])
    digest = hashlib.sha256(payload).hexdigest()
    dest = tmp_path / "t.tar.gz"
    (tmp_path / "t.tar.gz.part").write_bytes(payload[:10_000])  # an interrupted earlier attempt
    info = v2.download_stored_member(source, member, dest, expected_sha256=digest, chunk=50_000)
    assert dest.read_bytes() == payload and info["sha256"] == digest
    assert source.stats.bytes < len(payload) + 1000  # the first 10,000 bytes were not refetched

    bad = tmp_path / "bad.tar.gz"
    with pytest.raises(remote_zip.ZipIntegrityError):
        v2.download_stored_member(source, member, bad, expected_sha256="0" * 64)
    assert not bad.exists()


def test_design_power_is_computed_and_monotone() -> None:
    rows = v2.power_rule_d(
        n_clean=342,
        run1_only=23,
        run2_only=9,
        n_l_values=(20,),
        r_l_values=(0.1, 0.4),
        sims=200,
        seeds=(42,),
    )
    assert rows[0]["power_mean"] < rows[1]["power_mean"]
    pairs = [(10 + (i % 7), 10 + (i % 5)) for i in range(300)]
    power = v2.power_rule_a(pairs, n=200, ratios=(1.0, 1.5), sims=20, seeds=(42,))
    assert power[0]["power_mean"] <= power[1]["power_mean"]
    assert power[1]["power_mean"] > 0.5


def test_specificity_guard_drops_a_criterion_that_fires_on_passing_episodes() -> None:
    tasks = [f"t{i}" for i in range(20)]
    s1 = {t: 1.0 for t in tasks}
    s2 = {t: 1.0 for t in tasks}
    for t in tasks[:4]:
        s2[t] = 0.0
    h = {tag: {t: 1.0 for t in tasks} for tag in ("h1", "h2")}
    status1 = {t: {"trajectory_id": f"a{t}", "agp_message": "Completed"} for t in tasks}
    status2 = {t: {"trajectory_id": f"b{t}", "agp_message": "Completed"} for t in tasks}
    features = {}
    for t in tasks:  # every episode, passing or not, has three identical screenshots
        features[f"a{t}"] = v2.TrajectoryFeatures(f"a{t}", steps=20, parsed=True, identical_run=3)
        features[f"b{t}"] = v2.TrajectoryFeatures(f"b{t}", steps=20, parsed=True, identical_run=3)
    features["bt0"].env_text_hits = {"captcha": 1}
    out = v2.rules_abc(
        features=features, status1=status1, status2=status2, s1=s1, s2=s2, clean=tasks, h_rewards=h
    )
    guard = out["rule_b_specificity"]
    assert guard["share_firing"]["screenshots"] == 1.0
    assert guard["criteria_in_force"] == ["tool_error", "text"]
    assert out["rule_b_run2_unique_failures"]["classes"] == {"2_environment": 1, "5_other": 3}
    assert out["rule_b_run2_all_criteria_sensitivity"]["classes"] == {"2_environment": 4}
