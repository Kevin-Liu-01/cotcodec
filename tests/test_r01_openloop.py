"""R01 v2: Stage C open-loop replay and the A1 capture mode against a fake guest (CPU)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from harness.q2.vm import desktop
from harness.q2.vm.guest_http import GuestClient
from harness.q2_stage1 import driver
from harness.r01 import openloop
from tests.test_q2_stage1_driver import FakeGuest, FakeSession


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.t += s


class BlinkGuest(FakeGuest):
    def __init__(self, blink_value: str = "false") -> None:
        super().__init__()
        self.blink_value = blink_value

    def execute(self, argv: list[str]) -> dict[str, Any]:
        if argv[:2] == ["gsettings", "get"]:
            return {
                "status": "success",
                "error": "",
                "returncode": 0,
                "output": f"{self.blink_value}\n",
            }
        return super().execute(argv)


@pytest.fixture(autouse=True)
def fast(monkeypatch, tmp_path):
    monkeypatch.setattr(desktop, "RETRY_INTERVAL_S", 0.0)
    monkeypatch.setattr(driver, "GPU_DEVICE_GLOB", str(tmp_path / "none" / "nvidia*"))


@pytest.fixture
def guest():
    fake = BlinkGuest().start()
    yield fake
    fake.stop()


CLICK = [{"op": "click", "x": 500, "y": 500, "button": 1, "count": 1}]
RECORDED = [
    {
        "step": 1,
        "ir": CLICK,
        "ir_sha256": driver.sha256_json(CLICK),
        "latency_s": 2.0,
        "terminated": None,
    },
    {
        "step": 2,
        "ir": [],
        "ir_sha256": driver.sha256_json([]),
        "latency_s": 1.5,
        "terminated": None,
    },
    {
        "step": 3,
        "ir": CLICK,
        "ir_sha256": driver.sha256_json(CLICK),
        "latency_s": 2.5,
        "terminated": None,
    },
    {
        "step": 4,
        "ir": [{"op": "terminate", "status": "success"}],
        "ir_sha256": None,
        "latency_s": 1.0,
        "terminated": "success",
    },
]


def make(guest: FakeGuest, tmp_path: Path, mode: str, recorded=RECORDED, session=None, **cfg: Any):
    clock = Clock()
    session = session or FakeSession()
    config = openloop.OpenLoopConfig(
        job="R01-C",
        size="4B",
        session="S1",
        task_id="t-1",
        harness="H-OSW-fixed",
        rerun=1,
        attempt=1,
        extension_block=None,
        block="c1",
        slot="R01-C:t-1:r1",
        out_dir=str(tmp_path / "out"),
        guest_ip="127.0.0.1",
        server_port=guest.port,
        settle_after_reset_s=60.0,
        settle_before_eval_s=20.0,
        boot_timeout_s=0.5,
        r01_mode=mode,
        **cfg,
    )
    runner = openloop.OpenLoopRunner(
        config,
        guest=GuestClient("127.0.0.1", guest.port),
        session_factory=lambda c, t: session,
        task={"id": "t-1", "instruction": "x"},
        recorded=recorded,
        sleep=clock.sleep,
        clock=clock,
    )
    return runner, clock, session


def test_stage_c_replays_recorded_ir_with_frames_and_scores(guest, tmp_path):
    runner, clock, session = make(guest, tmp_path, "stage-c")
    record = runner.run()
    assert record["status"] == "scored" and record["score"] == 1.0
    assert record["ended"] == "terminate_success" and session.last_action == "DONE"
    labels = [f["label"] for f in record["frames"]]
    # step 2 had no action: no new f0 at step 3
    assert labels == ["s01-f0", "s01-f1", "s02-f0", "s02-f1", "s03-f1", "s04-f0", "s04-f1"]
    assert len(guest.executor_commands()) == 2  # two clicks, no model, no terminate command
    steps = [json.loads(x) for x in (tmp_path / "out" / "steps.jsonl").read_text().splitlines()]
    assert all(s["ir_matches_record"] for s in steps) and steps[-1]["terminated"] == "success"
    assert (tmp_path / "out" / "frames" / "s01-f0.png").exists()
    sums = (tmp_path / "out" / "frames.sha256").read_text().splitlines()
    assert len(sums) == 7
    assert record["schema"] == openloop.SCHEMA
    assert 60.0 in clock.slept and 20.0 in clock.slept


def test_stage_c_spaces_actions_by_the_recorded_latency(guest, tmp_path):
    runner, clock, _ = make(guest, tmp_path, "stage-c")
    runner.run()
    # waits: f1 at +0.6, then the rest of the step's latency (2.0 - 0.6 = 1.4)
    assert pytest.approx(clock.slept[clock.slept.index(60.0) + 1]) == 0.6
    assert pytest.approx(clock.slept[clock.slept.index(60.0) + 2]) == 1.4


def test_stage_c_without_recorded_steps_is_a_runner_loss(guest, tmp_path):
    runner, _, _ = make(guest, tmp_path, "stage-c", recorded=[])
    record = runner.run()
    assert record["status"] == "infrastructure" and record["infrastructure_type"] == "runner_crash"


def test_a1_captures_offsets_late_frame_and_one_open_loop_step(guest, tmp_path):
    runner, clock, session = make(
        guest, tmp_path, "a1", late_frame_s=61.0, open_loop_steps=1, blink_off=True
    )
    record = runner.run()
    assert record["status"] == "captured" and record["blink_off_check"]["get"] == "false"
    labels = [f["label"] for f in record["frames"]]
    assert labels == ["t+0.0", "t+0.6", "t+1.2", "t+61.0", "s02-f0", "s02-f1"]
    assert len(guest.executor_commands()) == 1
    assert session.last_action == "unset"  # no checker in A1
    assert [
        "gsettings",
        "set",
        "org.gnome.desktop.interface",
        "cursor-blink",
        "false",
    ] in guest.commands


def test_a1_blink_off_that_does_not_read_back_is_a_setup_loss(tmp_path):
    fake = BlinkGuest(blink_value="true").start()
    try:
        runner, _, _ = make(fake, tmp_path, "a1", blink_off=True)
        record = runner.run()
    finally:
        fake.stop()
    assert record["status"] == "infrastructure" and record["infrastructure_type"] == "task_setup"


def test_open_loop_config_rejects_unknown_keys():
    with pytest.raises(ValueError):
        openloop.OpenLoopConfig.from_json({"job": "x", "bogus": 1})


def test_load_recorded_reads_s1a_step_lines(tmp_path):
    path = tmp_path / "steps.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(
                {
                    "step": k,
                    "ir": CLICK,
                    "ir_sha256": "h",
                    "terminated": None,
                    "completion": {"latency_s": 1.5 + k},
                }
            )
            for k in (2, 1)
        )
        + "\n"
    )
    rows = openloop.load_recorded(path)
    assert [r["step"] for r in rows] == [1, 2] and rows[0]["latency_s"] == 2.5
