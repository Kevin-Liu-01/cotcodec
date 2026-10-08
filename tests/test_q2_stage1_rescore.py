"""Offline rescoring of captured states and the zinv validation gate (G0 items 6 and 8)."""

from __future__ import annotations

import hashlib
import json
import textwrap
from pathlib import Path

import pytest

from harness.q2_stage1 import rescore

FAKE_DESKTOP_ENV = """
import os


class DesktopEnv:
    def _set_task_info(self, task):
        self.task_id = task["id"]
        self.cache_dir = os.path.join(self.cache_dir_base, self.task_id)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.evaluator = task["evaluator"]
        from desktop_env.evaluators import metrics
        self.metric = getattr(metrics, self.evaluator["func"])

    def evaluate(self):
        if self.action_history and self.action_history[-1] == "FAIL":
            return 0
        data = self.controller.get_file(self.evaluator["result"]["path"])
        cached = open(os.path.join(self.cache_dir, "stdout.txt")).read()
        return self.metric(data, cached)
"""
FAKE_METRICS = """
from desktop_env.evaluators.metrics.slides import compare_pptx_files


def compare_text(data, cached):
    return 1.0 if data == b"good" and cached == "ok" else 0.0
"""
FAKE_SLIDES = """
def compare_pptx_files(data, cached, **options):
    return 0.0
"""


@pytest.fixture
def fake_osworld(tmp_path):
    root = tmp_path / "OSWorld"
    for rel, text in (
        ("desktop_env/__init__.py", ""),
        ("desktop_env/desktop_env.py", FAKE_DESKTOP_ENV),
        ("desktop_env/evaluators/__init__.py", ""),
        ("desktop_env/evaluators/metrics/__init__.py", FAKE_METRICS),
        ("desktop_env/evaluators/metrics/slides.py", FAKE_SLIDES),
    ):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text))
    return root


def capture(tmp_path: Path, content: bytes, history: list[str]) -> Path:
    episode = tmp_path / "episode"
    cap = episode / "capture"
    (cap / "vm" / "home/user").mkdir(parents=True)
    (cap / "vm" / "home/user/out.txt").write_bytes(content)
    (cap / "cache").mkdir()
    (cap / "cache" / "stdout.txt").write_text("ok")
    manifest = {
        "vm_files": {"/home/user/out.txt": hashlib.sha256(content).hexdigest()},
        "cache_files": {"stdout.txt": hashlib.sha256(b"ok").hexdigest()},
        "action_history": history,
        "state_sha256": "x",
    }
    (cap / "capture.json").write_text(json.dumps(manifest))
    return episode


TASK = {"id": "t1", "evaluator": {"func": "compare_text", "result": {"path": "/home/user/out.txt"}}}


def test_captured_state_rescored_offline_matches_live(tmp_path, fake_osworld):
    episode = capture(tmp_path, b"good", ["DONE"])
    record = {"slot": "s", "attempt": 1, "task_id": "t1", "score": 1.0}
    row = rescore.rescore_episode(
        episode, record, TASK, osworld=str(fake_osworld), file_cache=str(tmp_path), timeout=60
    )
    assert row["raw"] == 1.0 and row["raw_state"] == 1.0
    assert row["live_offline_match"] is True
    assert row["corrected_applies"] is False and row["corrected"] == row["raw"]


def test_fail_rule_and_state_score(tmp_path, fake_osworld):
    episode = capture(tmp_path, b"good", ["FAIL"])
    record = {"slot": "s", "attempt": 1, "task_id": "t1", "score": 0.0}
    row = rescore.rescore_episode(
        episode, record, TASK, osworld=str(fake_osworld), file_cache=str(tmp_path), timeout=60
    )
    assert row["raw"] == 0.0 and row["raw_state"] == 1.0


def test_tampered_capture_is_refused(tmp_path, fake_osworld):
    episode = capture(tmp_path, b"good", ["DONE"])
    (episode / "capture/vm/home/user/out.txt").write_bytes(b"edited")
    record = {"slot": "s", "attempt": 1, "task_id": "t1", "score": 1.0}
    row = rescore.rescore_episode(
        episode, record, TASK, osworld=str(fake_osworld), file_cache=str(tmp_path), timeout=60
    )
    assert row["raw"] is None and "does not match its digest" in row["raw_error"]


def test_corrected_rescoring_installs_zinv(tmp_path, fake_osworld):
    task = {"id": "t1", "evaluator": {"func": "compare_pptx_files",
                                      "result": {"path": "/home/user/out.txt"}}}  # fmt: skip
    episode = capture(tmp_path, b"good", ["DONE"])
    record = {"slot": "s", "attempt": 1, "task_id": "t1", "score": 0.0}
    row = rescore.rescore_episode(
        episode, record, task, osworld=str(fake_osworld), file_cache=str(tmp_path), timeout=60
    )
    assert row["corrected_applies"] is True
    assert row["raw"] == 0.0
    # The fake comparator gets bytes, not paths; zinv's alignment fails to read them and falls
    # back to the original verdict, so the corrected score equals the raw one here.
    assert row["corrected"] == 0.0 and "corrected_error" not in row


def test_merge_writes_corrected_scores():
    episodes = [
        {"slot": "a", "attempt": 1, "status": "scored", "score": 0.0},
        {"slot": "b", "attempt": 1, "status": "scored", "score": 0.0, "metric_exception": True},
        {"slot": "c", "attempt": 1, "status": "infrastructure", "score": None},
    ]
    rescored = [
        {"slot": "a", "attempt": 1, "corrected": 1.0, "raw": 0.0, "raw_state": 0.0,
         "live_offline_match": True},
        {"slot": "b", "attempt": 1, "corrected": 1.0, "raw": 0.0, "raw_state": 0.0,
         "live_offline_match": True},
    ]  # fmt: skip
    merged = list(rescore.merge(episodes, rescored))
    assert merged[0]["corrected_score"] == 1.0
    assert merged[1]["corrected_score"] == 0.0  # a metric exception stays 0
    assert "corrected_score" not in merged[2]


def rows(confirmed_pass: int = 29) -> list[dict]:
    out = []
    for i in range(29):
        z = 1.0 if i < confirmed_pass else 0.0
        out.append({"id": f"c{i}", "kind": "mutant", "operator": rescore.ZORDER,
                    "reading": "confirmed", "label": "should_pass_equiv", "stored": 0.0,
                    "raw": 0.0, "zinv": z})  # fmt: skip
    out.append({"id": "u", "kind": "mutant", "operator": rescore.ZORDER, "reading": "unresolved",
                "label": "should_pass_equiv", "stored": 0.0, "raw": 0.0, "zinv": 1.0})  # fmt: skip
    out.append({"id": "g", "kind": "gold", "operator": None, "reading": None, "label": "gold",
                "stored": 1.0, "raw": 1.0, "zinv": 1.0})  # fmt: skip
    out.append(
        {
            "id": "v",
            "kind": "mutant",
            "operator": "pptx.viol.text",
            "reading": None,
            "label": "should_fail_violation",
            "stored": 0.0,
            "raw": 0.0,
            "zinv": 0.0,
        }
    )
    return out


def test_validation_gate():
    gate = rescore.judge_validation(rows())
    assert gate["pass"] and gate["others"] == 2 and gate["unresolved_reported"]
    assert not rescore.judge_validation(rows(confirmed_pass=28))["pass"]
    bad = rows()
    bad[-1]["zinv"] = 1.0  # the correction turned a should-fail mutant into a pass
    gate = rescore.judge_validation(bad)
    assert not gate["pass"] and gate["others_differing"][0]["id"] == "v"


def test_validation_set_selects_compare_pptx_files_evaluable_items():
    jobs = [{"mutant_id": m, "task_id": "t", "files": {}} for m in ("m1", "m2", "m3")]
    verdicts = [
        {"mutant_id": "m1", "checker_funcs": ["compare_pptx_files"], "score": 0.0},
        {"mutant_id": "m2", "checker_funcs": ["compare_table"], "score": 1.0},
        {"mutant_id": "m3", "checker_funcs": ["compare_pptx_files"], "score": 1.0},
    ]
    outcomes = [{"mutant_id": "m1", "lock_status": "evaluable", "operator": rescore.ZORDER,
                 "label": "should_pass_equiv"},
                {"mutant_id": "m3", "lock_status": "save_failed"}]  # fmt: skip
    golds = [{"mutant_id": "g1", "task_id": "t", "kind": "gold", "files": {}}]
    gold_verdicts = [{"mutant_id": "g1", "checker_funcs": ["compare_pptx_files"], "score": 1.0}]
    candidates = [{"mutant_id": "m1", "audit_reading": "confirmed"}]
    items = rescore.validation_set(jobs, verdicts, outcomes, golds, gold_verdicts, candidates)
    assert [(i["kind"], i["job"]["mutant_id"], i["reading"]) for i in items] == [
        ("mutant", "m1", "confirmed"), ("gold", "g1", None)]  # fmt: skip


def test_remap_paths():
    job = {"files": {"/home/user/a.pptx": "/ro/lo/files/x/a.pptx", "/gone": None}}
    out = rescore.remap(job, {"/ro/lo/": "/ro/clo/"})
    assert out["files"] == {"/home/user/a.pptx": "/ro/clo/files/x/a.pptx", "/gone": None}
