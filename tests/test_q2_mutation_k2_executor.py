"""The K2 injection executor end to end against a fake VM, guest and OSWorld session."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from harness.q2.vm.suite import guest_source
from harness.q2_mutation.reachability import window_title_for
from harness.q2_mutation_k2 import executor, rules
from harness.q2_stage1 import driver
from harness.q2_stage1.osworld_live import TransportFailure

CTRL_S = ["python", "-c", 'import pyautogui; pyautogui.hotkey("ctrl", "s");']
CALC = {
    "id": "01b269ae-2111-4a07-81fd-3fcd711993b0",
    "config": [
        {"type": "download", "parameters": {"files": [{"url": "u", "path": "/home/user/A.xlsx"}]}},
        {"type": "open", "parameters": {"path": "/home/user/A.xlsx"}},
    ],
    "evaluator": {
        "postconfig": [
            {
                "type": "activate_window",
                "parameters": {"window_name": "A.xlsx - LibreOffice Calc", "strict": True},
            },
            {"type": "sleep", "parameters": {"seconds": 0.5}},
            {"type": "execute", "parameters": {"command": CTRL_S}},
            {"type": "sleep", "parameters": {"seconds": 0.5}},
        ],
        "func": "compare_table",
        "result": {"type": "vm_file", "path": "/home/user/A.xlsx", "dest": "A.xlsx"},
    },
}
AGENT = {
    "id": "936321ce-0000-0000-0000-000000000000",
    "config": [
        {
            "type": "download",
            "parameters": {"files": [{"url": "u", "path": "/home/user/Desktop/B.docx"}]},
        },
        {"type": "open", "parameters": {"path": "/home/user/Desktop/B.docx"}},
    ],
    "evaluator": {
        "postconfig": [
            {
                "type": "activate_window",
                "parameters": {"window_name": "B_Gold.docx - LibreOffice Writer", "strict": True},
            },
            {"type": "execute", "parameters": {"command": CTRL_S}},
        ],
        "func": "compare_docx_files",
        "result": {"type": "vm_file", "path": "/home/user/Desktop/B.docx", "dest": "B.docx"},
    },
}
CONVERT = [
    "libreoffice",
    "--convert-to",
    "csv:Text - txt - csv (StarCalc):44,34,UTF-8,,,,false,true,true,false,false,1",
    "--outdir",
    "/home/user",
    "/home/user/C.xlsx",
]
DERIVED = {
    "id": "6e99a1ad-0000-0000-0000-000000000000",
    "config": [
        {"type": "download", "parameters": {"files": [{"url": "u", "path": "/home/user/C.xlsx"}]}},
        {"type": "open", "parameters": {"path": "/home/user/C.xlsx"}},
    ],
    "evaluator": {
        "postconfig": [
            {
                "type": "activate_window",
                "parameters": {"window_name": "C.xlsx - LibreOffice Calc", "strict": True},
            },
            {"type": "execute", "parameters": {"command": CTRL_S}},
            {"type": "execute", "parameters": {"command": CONVERT}},
        ],
        "func": ["compare_table", "compare_csv"],
        "result": [
            {"type": "vm_file", "path": "/home/user/C.xlsx", "dest": "C.xlsx"},
            {"type": "vm_file", "path": "/home/user/C-Sheet1.csv", "dest": "C.csv"},
        ],
    },
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Clock:
    def __init__(self) -> None:
        self.t = 1_000.0

    def __call__(self) -> float:
        self.t += 0.01
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


class FakeVM:
    """The guest's files, LibreOffice's open documents and windows, and the save behaviour."""

    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.files: dict[str, bytes] = {}
        self.mtimes: dict[str, int] = {}
        self.docs: list[str] = []
        self.focused: str | None = None
        self.extra_windows: list[str] = []
        self.kill_fails = False
        self.corrupt_upload = False
        self.late_save = False
        self.never_save = False
        self.pending: list[str] = []
        self.dialog_after_open = False
        self.log: list[tuple[str, Any]] = []

    def write(self, path: str, data: bytes) -> None:
        self.files[path] = data
        self.mtimes[path] = int(self.clock.t * 1e9) + len(self.mtimes)

    def flush(self) -> None:
        for path in self.pending:
            self.write(path, self.files[path] + b"|saved")
        self.pending.clear()

    # VMOps ---------------------------------------------------------------
    def hash(self, paths: list[str]) -> dict[str, Any]:
        self.flush()
        rows = []
        for p in paths:
            data = self.files.get(p)
            rows.append(
                {
                    "path": p,
                    "exists": data is not None,
                    "sha256": sha(data) if data is not None else None,
                    "size": len(data) if data is not None else None,
                    "mtime_ns": self.mtimes.get(p),
                }
            )
        return {"files": rows, "guest_time": self.clock.t + 3.0}

    def close_app(self, name: str) -> dict[str, Any]:
        self.log.append(("close_app", name))
        found = [{"pid": 100 + i, "comm": "soffice.bin"} for i, _ in enumerate(self.docs)]
        if self.kill_fails:
            return {"found": found, "term": [100], "kill": [100], "remaining": found[:1]}
        self.docs.clear()
        self.focused = None
        return {"found": found, "term": [p["pid"] for p in found], "kill": [], "remaining": []}

    def remove_locks(self, paths: list[str]) -> dict[str, Any]:
        return {"removed": []}

    def windows(self) -> list[str]:
        return [window_title_for(p) or p for p in self.docs] + list(self.extra_windows)

    def wait_written(self, path: str, before: dict, timeout: float) -> dict[str, Any]:
        self.flush()
        now = (self.mtimes.get(path), len(self.files.get(path, b"")))
        changed = now != (before.get("mtime_ns"), before.get("size"))
        return {"seconds": 0.4 if changed else None, "state": {"sha256": sha(self.files[path])}}

    def upload(self, path: str, local: str) -> dict[str, Any]:
        data = Path(local).read_bytes()
        self.write(path, data + (b"x" if self.corrupt_upload else b""))
        self.log.append(("upload", path))
        return {"ok": True, "replies": [{"status": 200, "type": "upload_file"}], "failures": []}

    def run_steps(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        replies = []
        for step in steps:
            kind, params = step["type"], step.get("parameters", {})
            self.log.append((kind, params))
            if kind == "open":
                if params["path"] not in self.files:
                    raise RuntimeError(f"Setup step 1 failed: open {params['path']}")
                self.open(params["path"])
            elif kind == "activate_window":
                for doc in self.docs:
                    if window_title_for(doc) == params["window_name"]:
                        self.focused = doc
            elif kind == "execute" and params["command"] == CTRL_S:
                self.ctrl_s()
            elif kind == "execute" and "--convert-to" in params["command"]:
                self.write("/home/user/C-Sheet1.csv", b"csv:" + self.files["/home/user/C.xlsx"])
            replies.append({"status": 200, "type": kind, "t": self.clock.t})
        return {"ok": True, "replies": replies, "failures": []}

    def open(self, path: str) -> None:
        if path not in self.docs:
            self.docs.append(path)
        self.focused = path
        if self.dialog_after_open:
            self.extra_windows.append("LibreOffice Document Recovery")

    def ctrl_s(self) -> None:
        if self.focused is None or self.never_save:
            return
        if self.late_save:
            self.pending.append(self.focused)
        else:
            self.write(self.focused, self.files[self.focused] + b"|saved")


class FakeSession:
    """OSWorld's side: setup through the fake VM, evaluate (postconfig, then the checker)."""

    def __init__(self, task: dict[str, Any], vm: FakeVM) -> None:
        self.task = task
        self.vm = vm
        self.reads: list[tuple[str, str | None]] = []
        self.raise_in_evaluate: BaseException | None = None
        self.setup_failures: list[str] = []
        self.evaluate_replies: list[dict[str, Any]] = []

    def setup(self) -> dict[str, Any]:
        for step in self.task["config"]:
            if step["type"] == "download":
                for f in step["parameters"]["files"]:
                    self.vm.write(f["path"], b"initial")
            elif step["type"] == "open":
                self.vm.open(step["parameters"]["path"])
        return {"steps": len(self.task["config"]), "replies": [], "failures": self.setup_failures}

    def evaluate(self, last_action: str | None) -> Any:
        assert last_action == "DONE"
        result = self.vm.run_steps(self.task["evaluator"].get("postconfig", []))
        self.evaluate_replies = result["replies"]
        if self.raise_in_evaluate is not None:
            raise self.raise_in_evaluate
        results = self.task["evaluator"]["result"]
        score = 1.0
        for getter in results if isinstance(results, list) else [results]:
            data = self.vm.files.get(getter["path"])
            self.reads.append((getter["path"], sha(data) if data is not None else None))
            if data is None or b"GOOD" not in data or b"|saved" not in data:
                score = 0.0
        return score

    def read_count(self) -> int:
        return len(self.reads)

    def checker_reads_since(self, index: int) -> dict[str, str | None]:
        return dict(self.reads[index:])

    def capture_sweep(self) -> list[dict[str, Any]]:
        return []

    def write_capture(self, capture_dir: Path) -> dict[str, Any]:
        capture_dir.mkdir(parents=True, exist_ok=True)
        return {"state_sha256": "f" * 64}

    def observation_summary(self) -> dict[str, Any]:
        return {"calls": len(self.reads), "undelivered": 0}

    def close(self) -> None:
        return None


class FakeGuest:
    """The guest endpoints S1a's boot wait, warm-up and restart checks call."""

    def __init__(self) -> None:
        self.pid = 4242
        self.restart_after_warmup = False
        self.warmups = 0

    def screenshot(self, timeout: float = 10.0) -> tuple[int, bytes, float]:
        return 200, b"\x89PNG\r\n\x1a\n" + b"0" * 64, 0.01

    def run_script(self, source: str, args: list[str] | None = None) -> dict[str, Any]:
        if source == guest_source("guard.py"):
            self.warmups += 1
            return {"keycode": 250, "shell": {"idle": True}, "server_pid": self.pid}
        if source == driver.SERVER_PID_SCRIPT:
            return {"server_pid": self.pid + (1 if self.restart_after_warmup else 0)}
        raise AssertionError("unexpected guest script")

    def execute(self, argv: list[str], timeout: float = 130.0) -> dict[str, Any]:
        if argv[0] == "cat":
            unit = "0::/user.slice/user@1000.service/app.slice/osworld_server.service\n"
            return {"http_status": 200, "output": unit}
        return {"http_status": 200, "output": "0\n"}


def make(
    tmp_path: Path, task: dict[str, Any], files: dict[str, bytes], target: str, **cfg: Any
) -> tuple[executor.Injector, FakeVM, FakeSession, FakeGuest]:
    clock = Clock()
    vm = FakeVM(clock)
    session = FakeSession(task, vm)
    guest = FakeGuest()
    entries = {}
    for vm_path, data in files.items():
        local = tmp_path / "cand" / vm_path.lstrip("/")
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
        entries[vm_path] = {"local": str(local), "sha256": sha(data)}
    config = executor.K2Config(
        lane="test",
        purpose="development",
        slot="k2:000:r1",
        set="k2",
        pair=0,
        run=1,
        attempt=1,
        block="r1",
        job_id="job",
        mutant_id="job",
        task_id=task["id"],
        kind="mutant",
        candidate_sha256=sha(files[target]),
        files=entries,
        out_dir=str(tmp_path / "out"),
        **cfg,
    )
    injector = executor.Injector(
        config,
        guest=guest,
        task=task,
        session_factory=lambda c, t: session,
        ops_factory=lambda g, s: vm,
        sleep=clock.sleep,
        clock=clock,
        gpu_glob=lambda: [],
    )
    return injector, vm, session, guest


def test_postconfig_save_task_is_scored_through_the_frozen_plan(tmp_path: Path) -> None:
    injector, vm, _, guest = make(
        tmp_path, CALC, {"/home/user/A.xlsx": b"GOOD"}, "/home/user/A.xlsx"
    )
    record = injector.run()
    assert record["status"] == "scored", record.get("infrastructure_detail")
    assert record["verdict"] == "pass" and record["exclusion"] is None
    assert record["schema"] == rules.RUN_SCHEMA
    assert record["plan_ops"] == [
        "reset_task",
        "kill_process",
        "assert_no_window",
        "hash",
        "upload",
        "hash",
        "config_step",
        "hash",
        "postconfig",
        "hash",
        "evaluate",
    ]
    assert record["save_paths"] == {"/home/user/A.xlsx": "postconfig_save"}
    assert record["hashes"]["post_inject"]["/home/user/A.xlsx"] == sha(b"GOOD")
    assert record["hashes"]["pre_inject"]["/home/user/A.xlsx"] == sha(b"initial")
    assert record["unsaved_at_read"] == [] and record["late_write"] == {}
    assert record["post_postconfig"]["/home/user/A.xlsx"] == sha(b"GOOD|saved")
    assert guest.warmups == 1
    assert record["timings"]["settle_after_reset_s"] == pytest.approx(60.0, abs=0.1)
    assert record["timings"]["settle_before_eval_s"] == pytest.approx(20.0, abs=0.1)
    ops = [entry[0] for entry in vm.log]
    # The application is closed before the file is replaced, and reopened after.
    assert ops.index("close_app") < ops.index("upload") < ops.index("open")
    assert json.loads((tmp_path / "out" / "k2-run.json").read_text())["verdict"] == "pass"


def test_hash_mismatch_after_injection_is_cause_3(tmp_path: Path) -> None:
    injector, vm, _, _ = make(tmp_path, CALC, {"/home/user/A.xlsx": b"GOOD"}, "/home/user/A.xlsx")
    vm.corrupt_upload = True
    record = injector.run()
    assert record["status"] == "infrastructure"
    assert record["exclusion"] == rules.HASH_MISMATCH
    assert rules.run_state(record) == {"state": "excluded", "cause": rules.HASH_MISMATCH}


@pytest.mark.parametrize(
    ("setup", "step"),
    [
        (lambda vm, s, g: setattr(vm, "kill_fails", True), "executor:kill_process"),
        (lambda vm, s, g: setattr(vm, "dialog_after_open", True), "executor:config_step"),
        (lambda vm, s, g: s.setup_failures.append("download HTTP 500"), "executor:reset_task"),
        (
            lambda vm, s, g: setattr(s, "raise_in_evaluate", TransportFailure("gone")),
            "executor:evaluate",
        ),
        (lambda vm, s, g: setattr(g, "restart_after_warmup", True), "guest_server_restart"),
    ],
)
def test_executor_and_vm_failures_are_cause_4(tmp_path: Path, setup: Any, step: str) -> None:
    injector, vm, session, guest = make(
        tmp_path, CALC, {"/home/user/A.xlsx": b"GOOD"}, "/home/user/A.xlsx"
    )
    setup(vm, session, guest)
    record = injector.run()
    assert record["status"] == "infrastructure"
    assert record["exclusion"] == rules.VM_INFRA
    assert record["infrastructure_type"] == step
    assert record["verdict"] is None


def test_a_candidate_file_that_differs_from_its_digest_never_reaches_the_vm(tmp_path: Path) -> None:
    injector, vm, _, _ = make(tmp_path, CALC, {"/home/user/A.xlsx": b"GOOD"}, "/home/user/A.xlsx")
    Path(injector.cfg.files["/home/user/A.xlsx"]["local"]).write_bytes(b"other")
    record = injector.run()
    assert record["infrastructure_type"] == "executor:candidate"
    assert not any(entry[0] == "upload" for entry in vm.log)


def test_a_save_that_lands_after_the_checker_read_is_cause_1_evidence(tmp_path: Path) -> None:
    injector, vm, _, _ = make(tmp_path, CALC, {"/home/user/A.xlsx": b"GOOD"}, "/home/user/A.xlsx")
    vm.late_save = True
    record = injector.run()
    assert record["status"] == "scored" and record["verdict"] == "fail"
    assert record["unsaved_at_read"] == ["/home/user/A.xlsx"]
    assert record["late_write"]["/home/user/A.xlsx"]["changed"] is True
    assert rules.save_late(record) is True
    runs = [rules.run_reading([record])]
    pair = rules.classify_pair(runs, "pass", False)
    assert pair["state"] == "differ" and pair["explanation"] == rules.SAVE_LATE


def test_a_save_that_never_writes_is_not_cause_1(tmp_path: Path) -> None:
    injector, vm, _, _ = make(tmp_path, CALC, {"/home/user/A.xlsx": b"GOOD"}, "/home/user/A.xlsx")
    vm.never_save = True
    record = injector.run()
    assert record["status"] == "scored" and record["verdict"] == "fail"
    assert record["late_write"]["/home/user/A.xlsx"]["changed"] is False
    pair = rules.classify_pair([rules.run_reading([record])], "pass", False)
    assert pair["explanation"] == rules.UNEXPLAINED


def test_agent_save_task_saves_before_the_postconfig(tmp_path: Path) -> None:
    injector, vm, _, _ = make(
        tmp_path, AGENT, {"/home/user/Desktop/B.docx": b"GOOD"}, "/home/user/Desktop/B.docx"
    )
    record = injector.run()
    assert record["status"] == "scored", record.get("infrastructure_detail")
    assert record["save_paths"] == {"/home/user/Desktop/B.docx": "agent_save"}
    assert "agent_save" in record["plan_ops"]
    saves = [s for s in record["steps"] if s["op"] == "agent_save"]
    assert saves and saves[0]["seconds_to_write"] == 0.4
    activations = [p for kind, p in vm.log if kind == "activate_window"]
    assert {"window_name": "B.docx - LibreOffice Writer", "strict": True} in activations
    assert record["verdict"] == "pass"


def test_postconfig_outputs_are_left_to_the_postconfig(tmp_path: Path) -> None:
    files = {"/home/user/C.xlsx": b"GOOD", "/home/user/C-Sheet1.csv": b"gold csv"}
    injector, vm, _, _ = make(tmp_path, DERIVED, files, "/home/user/C.xlsx")
    record = injector.run()
    assert record["status"] == "scored", record.get("infrastructure_detail")
    assert record["derived_not_uploaded"] == ["/home/user/C-Sheet1.csv"]
    assert [p for kind, p in vm.log if kind == "upload"] == ["/home/user/C.xlsx"]
    assert vm.files["/home/user/C-Sheet1.csv"] == b"csv:GOOD|saved"


def test_a_metric_that_raises_is_the_error_verdict_not_an_exclusion(tmp_path: Path) -> None:
    injector, _, session, _ = make(
        tmp_path, CALC, {"/home/user/A.xlsx": b"GOOD"}, "/home/user/A.xlsx"
    )
    session.raise_in_evaluate = ValueError("bad sheet")
    record = injector.run()
    assert record["status"] == "scored" and record["verdict"] == "error"
    assert record["metric_error"].startswith("ValueError")


def test_derived_paths_follow_the_offline_conversion_rule() -> None:
    paths = [
        "/home/user/C.xlsx",
        "/home/user/C-Sheet1.csv",
        "/home/user/C.csv",
        "/home/user/Desktop/C-Sheet1.csv",
        "/home/user/D-Sheet1.csv",
    ]
    assert executor.derived_paths(DERIVED, paths) == ["/home/user/C-Sheet1.csv", "/home/user/C.csv"]
    assert executor.derived_paths(CALC, ["/home/user/A.xlsx"]) == []


def test_live_ops_send_the_guest_helper_and_the_pinned_setup_steps() -> None:
    class Guest:
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def run_script(self, source: str, args: list[str]) -> dict[str, Any]:
            assert source == executor.GUEST_SCRIPT.read_text()
            self.calls.append(args)
            return {"returncode": 0, "titles": ["A.xlsx - LibreOffice Calc"]}

    class Session:
        def __init__(self) -> None:
            self.steps: list[Any] = []

        def run_steps(self, steps: list[Any]) -> dict[str, Any]:
            self.steps += steps
            return {"ok": True, "replies": [], "failures": []}

    guest, session = Guest(), Session()
    ops = executor.LiveOps(guest, session)
    assert ops.windows() == ["A.xlsx - LibreOffice Calc"]
    ops.upload("/home/user/A.xlsx", "/inputs/candidates/m/home/user/A.xlsx")
    assert session.steps == [
        {
            "type": "upload_file",
            "parameters": {
                "files": [
                    {
                        "local_path": "/inputs/candidates/m/home/user/A.xlsx",
                        "path": "/home/user/A.xlsx",
                    }
                ]
            },
        }
    ]
    ops.close_app("soffice")
    assert guest.calls[-1][0] == "close_app"


def test_the_guest_helper_hashes_closes_and_waits(tmp_path: Path) -> None:
    import subprocess
    import sys
    import time

    source = executor.GUEST_SCRIPT
    target = tmp_path / "a.xlsx"
    target.write_bytes(b"one")

    def call(mode: str, config: dict[str, Any]) -> dict[str, Any]:
        out = subprocess.run(
            [sys.executable, str(source), mode, json.dumps(config)],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(out.stdout.strip().splitlines()[-1])

    state = call("hash", {"paths": [str(target), str(tmp_path / "none")]})
    assert state["files"][0]["sha256"] == sha(b"one") and state["files"][1]["exists"] is False
    lock = tmp_path / ".~lock.a.xlsx#"
    lock.write_text("x")
    assert call("remove_locks", {"paths": [str(target)]})["removed"] == [str(lock)]
    before = state["files"][0]
    assert (
        call("wait_written", {**before, "path": str(target), "timeout_s": 0.3})["seconds"] is None
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            f"import time; time.sleep(1); open({str(target)!r}, 'wb').write(b'two')",
        ]
    )
    waited = call("wait_written", {**before, "path": str(target), "timeout_s": 10})
    proc.wait()
    assert waited["seconds"] is not None and waited["state"]["sha256"] == sha(b"two")
    if not Path("/proc").is_dir():
        return  # close_app reads /proc (the guest is Linux)
    import shutil

    binary = tmp_path / "k2sleeptest"
    shutil.copy(shutil.which("sleep") or "/bin/sleep", binary)
    sleeper = subprocess.Popen([str(binary), "30"])
    time.sleep(0.2)
    closed = call("close_app", {"name": "k2sleeptest", "term_wait_s": 5})
    assert sleeper.wait(5) is not None
    assert sleeper.pid in closed["term"] and closed["remaining"] == []
