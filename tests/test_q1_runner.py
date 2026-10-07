"""Runner: kill-and-resume, signal checkpoint marker, watchdog and crash rows.

Spawns real worker processes on CPU (torch and triton required).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

os.environ.setdefault("TRITON_INTERPRET", "1")
torch = pytest.importorskip("torch")
pytest.importorskip("triton")
if torch.cuda.is_available():  # pragma: no cover - CPU-only fixtures
    pytest.skip("fixtures are CPU-only", allow_module_level=True)

from harness.q1 import doctor_fixtures as fx  # noqa: E402
from harness.q1.journal import Journal  # noqa: E402
from harness.q1.runner import Runner, RunnerConfig, WorkItem  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _items(tmp_path: Path, names: list[str], gates: tuple[str, ...]) -> list[WorkItem]:
    items = []
    for name in names:
        spec = fx.KERNELS[name]
        problem_id = str(spec["problem"])
        problem = tmp_path / f"{name}_problem.py"
        kernel = tmp_path / f"{name}_kernel.py"
        problem.write_text(fx.PROBLEMS[problem_id])
        kernel.write_text(str(spec["source"]))
        for gate in gates:
            items.append(
                WorkItem(
                    kernel_id=f"t-{name}",
                    kernel_path=str(kernel),
                    problem_id=problem_id,
                    gate=gate,
                    problem_source_path=str(problem),
                )
            )
    return items


def _write_items(path: Path, items: list[WorkItem]) -> None:
    path.write_text("".join(json.dumps(item.__dict__) + "\n" for item in items))


def _cli(items_path: Path, journal: Path, marker: Path, slots: str = "cpu") -> subprocess.Popen:
    env = {**os.environ, "TRITON_INTERPRET": "1", "PYTHONPATH": str(ROOT)}
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "harness.q1.runner",
            "--items",
            str(items_path),
            "--journal",
            str(journal),
            "--slots",
            slots,
            "--run-id",
            "resume-test",
            "--checkpoint-marker",
            str(marker),
            "--workdir",
            str(items_path.parent),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def test_kill_and_resume_finishes_every_item_once(tmp_path: Path) -> None:
    names = ["relu_correct", "relu_identity_control", "relu_cached", "argmax_control"]
    items = _items(tmp_path, names, ("a", "a_static"))
    items_path = tmp_path / "items.jsonl"
    _write_items(items_path, items)
    journal_path, marker = tmp_path / "journal.jsonl", tmp_path / "checkpoint.ready"
    first = _cli(items_path, journal_path, marker)
    deadline = time.time() + 120
    while time.time() < deadline:
        if journal_path.exists() and len(Journal(journal_path).status()) >= 2:
            break
        time.sleep(0.2)
    first.send_signal(signal.SIGKILL)  # no chance to checkpoint
    first.wait()
    with journal_path.open("ab") as handle:
        handle.write(b'{"kernel_id": "torn')  # simulate a write cut mid-line
    done_before = {k for k, v in Journal(journal_path).status().items() if v["final"]}
    assert 0 < len(done_before) < len(items)
    second = _cli(items_path, journal_path, marker)
    out, _ = second.communicate(timeout=600)
    assert second.returncode == 0, out
    summary = json.loads(out.decode().strip().splitlines()[-1])
    assert summary["skipped"] == len(done_before)
    journal = Journal(journal_path)
    status = journal.status()
    assert {i.key for i in items} == {k for k, v in status.items() if v["final"]}
    finals = [r for r in journal.final_rows() if r["details"].get("item_final")]
    assert len(finals) == len(items)
    _, invalid = journal.read()
    assert invalid == 1
    assert not marker.exists()  # no signal arrived: the marker is reserved for signals
    progress = json.loads((tmp_path / "progress.json").read_text())
    assert progress["items_final"] == len(items)


def test_sigusr1_checkpoints_and_exits_75(tmp_path: Path) -> None:
    items = _items(tmp_path, ["relu_correct", "relu_hang"], ("a",))
    items_path = tmp_path / "items.jsonl"
    _write_items(items_path, list(reversed(items)))  # the hang first, so it is running
    journal_path, marker = tmp_path / "journal.jsonl", tmp_path / "checkpoint.ready"
    process = _cli(items_path, journal_path, marker)
    time.sleep(8)
    process.send_signal(signal.SIGUSR1)
    out, _ = process.communicate(timeout=120)
    assert process.returncode == 75, out
    lines = marker.read_text().splitlines()
    assert lines[0] == "trigger=SIGUSR1"
    assert "run_id=resume-test" in lines
    hang_key = items[1].key
    assert hang_key not in Journal(journal_path).status()  # killed item not journaled


def test_watchdog_timeout_and_crash_rows(tmp_path: Path) -> None:
    items = _items(tmp_path, ["relu_hang", "relu_crash"], ("a",))
    config = RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        slots=["cpu", "cpu"],
        timeouts={"compile": 120.0, "correctness": 3.0, "timing": 10.0},
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=tmp_path,
    )
    summary = Runner(config).run(items)
    assert summary["timeouts"] == 1 and summary["crashes"] == 1
    rows = {r["kernel_id"]: r for r in Journal(config.journal_path).final_rows()}
    hang, crash = rows["t-relu_hang"], rows["t-relu_crash"]
    assert hang["verdict"] == "timeout" and hang["details"]["phase"] == "correctness"
    assert hang["wall_seconds"] < 60
    assert crash["verdict"] == "reject" and crash["details"]["reason"] == "worker-crashed"


def test_harness_row_fault_is_retried_once_and_never_a_rejection(tmp_path: Path) -> None:
    """A row the schema refuses is a harness fault: two attempts, both ``error``."""
    from harness.q1 import problems as problem_lib
    from harness.q1 import shapes

    items = _items(tmp_path, ["relu_correct"], ("A3",))
    problem_id = items[0].problem_id
    source = fx.PROBLEMS[problem_id]
    analysis = problem_lib.analyze_problem(problem_id, source)
    entry = shapes.build_problem_manifest(
        analysis,
        problem_sha256="0" * 64,
        input_bytes=lambda o: int(
            problem_lib.meta_input_summary(problem_lib.override_constants(source, analysis, o))[
                "input_bytes"
            ]
        ),
    )
    entry["A3"][0]["config_id"] = "A3/lead[1]"  # not allowed by schema.CONFIG_ID_RE
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"problems": {problem_id: entry}}))
    items[0].options = {"manifest_path": str(manifest)}
    config = RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=tmp_path,
    )
    summary = Runner(config).run(items)
    assert summary["infra_failures"] == 2 and summary["crashes"] == 0
    journal = Journal(config.journal_path)
    rows, _ = journal.read()
    assert [r["attempt"] for r in rows] == [1, 2]
    (final,) = journal.final_rows()
    assert final["verdict"] == "error" and final["attempt"] == 2
    assert final["details"]["reason"] == "infra_failure-harness-row"


def test_gate_c_runs_tuple_element_roots_end_to_end(tmp_path: Path) -> None:
    """Review finding: c3 ids built from ``input_shape[0]`` crashed the worker, so gate (c)
    rejected a correct kernel on 10 L1 problems. Shrunk L1/89 cumsum through the runner."""
    from harness.q1 import problems as problem_lib
    from harness.q1 import shapes

    problem_id = "L1/89_cumsum"
    source = problem_lib.load_problem_source(problem_id)
    small = source.replace("batch_size = 32768", "batch_size = 64").replace(
        "input_shape = (32768,)", "input_shape = (64,)"
    )
    assert small != source
    analysis = problem_lib.analyze_problem(problem_id, small)
    entry = shapes.build_problem_manifest(
        analysis,
        problem_sha256="0" * 64,
        input_bytes=lambda o: int(
            problem_lib.meta_input_summary(problem_lib.override_constants(small, analysis, o))[
                "input_bytes"
            ]
        ),
    )
    assert "c3/U1/input_shape.0" in {c["config_id"] for c in entry["c3"]}
    (tmp_path / "problem.py").write_text(small)
    (tmp_path / "manifest.json").write_text(json.dumps({"problems": {problem_id: entry}}))
    kernel = tmp_path / "kernel.py"
    kernel.write_text(
        small + "\n\nclass ModelNew(Model):\n    def forward(self, x):\n"
        "        return torch.cumsum(x, dim=self.dim)\n"
    )
    items = [
        WorkItem(
            kernel_id="correct-cumsum",
            kernel_path=str(kernel),
            problem_id=problem_id,
            gate="c",
            problem_source_path=str(tmp_path / "problem.py"),
            options={"manifest_path": str(tmp_path / "manifest.json")},
        )
    ]
    config = RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=tmp_path,
    )
    summary = Runner(config).run(items)
    assert summary["crashes"] == 0
    rows = Journal(config.journal_path).final_rows()
    aggregates = {r["gate"]: r["verdict"] for r in rows if r["config_id"] == "aggregate"}
    assert aggregates["c3"] == "accept" and aggregates["c2"] == "accept", aggregates
    assert any("input_shape.0" in r["config_id"] for r in rows if r["gate"] == "c3")


def test_rows_record_item_wall_seconds(tmp_path: Path) -> None:
    """Cost card input: every row carries spawn-to-verdict seconds."""
    items = _items(tmp_path, ["relu_correct", "relu_crash"], ("a",))
    config = RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=tmp_path,
    )
    Runner(config).run(items)
    rows = Journal(config.journal_path).final_rows()
    assert rows and all(row["details"]["item_wall_seconds"] > 0 for row in rows)


def test_soft_deadline_leaves_items_queued(tmp_path: Path) -> None:
    items = _items(tmp_path, ["relu_correct"], ("a", "a_1e-3", "a_head_1e-4"))
    config = RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=tmp_path,
        soft_deadline=time.monotonic() - 1.0,
    )
    summary = Runner(config).run(items)
    assert summary["run"] == 0 and summary["left_in_queue"] == 3 and summary["time_boxed"]
    assert not Journal(config.journal_path).final_rows()


def test_hard_deadline_kills_without_journaling_or_marker(tmp_path: Path) -> None:
    items = _items(tmp_path, ["relu_hang"], ("a",))
    marker = tmp_path / "checkpoint.ready"
    config = RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        timeouts={"compile": 120.0, "correctness": 120.0, "timing": 10.0},
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=tmp_path,
        checkpoint_marker=marker,
        hard_deadline=time.monotonic() + 8.0,
    )
    runner = Runner(config)
    started = time.monotonic()
    summary = runner.run(items)
    assert time.monotonic() - started < 60
    assert summary["time_boxed"] and runner.expired
    assert not Journal(config.journal_path).final_rows()
    assert runner.write_checkpoint_marker() is False and not marker.exists()


def test_exclusive_items_never_overlap_others(tmp_path: Path) -> None:
    items = _items(tmp_path, ["relu_correct"], ("a", "a_1e-3", "a_head_1e-4", "a_head_1e-2"))
    items[1].exclusive = True
    config = RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        slots=["cpu", "cpu", "cpu"],
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=tmp_path,
    )
    Runner(config).run(items)
    spans = {
        row["gate"]: (row["details"]["item_started_at"], row["details"]["item_ended_at"])
        for row in Journal(config.journal_path).final_rows()
    }
    start, end = spans.pop(items[1].gate)
    assert len(spans) == 3
    for other_start, other_end in spans.values():
        assert other_end <= start + 0.01 or other_start >= end - 0.01
