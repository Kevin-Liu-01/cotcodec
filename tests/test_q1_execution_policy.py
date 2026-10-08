"""Execution policy ``q1-stage0-exec/2`` and the runner's contention handling
(D31 review, findings 1 and 5). Pure Python: no torch, no GPU.

- memory-aware capacity units (``harness.q1.memory``) and the plan's use of them;
- the runner's free-memory guard (``MemoryGuard``) and device shares;
- a health check that drains the device and repeats alone before any slot stops,
  and never stops one on contention (``Runner._recover``);
- one resource-failure marker list for the runner and the reference store;
- the reference-store schedule's entry estimates, caps and disk footprint, and
  the driver's janitor that deletes an entry's tensors after its last consumer;
- the cost card's concurrency multiplier and the ledger's Stage 0 spend.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest

from harness.q1 import cost_card, faults, memory, refschedule, refstore, runner, trim
from harness.q1.journal import Journal
from harness.q1.runner import (
    DeviceShare,
    MemoryGuard,
    Runner,
    RunnerConfig,
    WorkItem,
    classify_health,
    contention_failure,
)
from harness.q1.schema import make_verdict_row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

L2_59 = "L2/59_Matmul_Swish_Scaling"
L2_87 = "L2/87_Conv2d_Subtract_Subtract_Mish"
L2_100 = "L2/100_ConvTranspose3d_Clamp_Min_Divide"
L1_10 = "L1/10_3D_tensor_matrix_multiplication"
L2_95 = "L2/95_Matmul_Add_Swish_Tanh_GELU_Hardtanh"
L1_19 = "L1/19_ReLU"


# --- memory-aware units ----------------------------------------------------------------


def test_units_follow_memory_not_input_bytes() -> None:
    """The three problems that ran out of memory at 12 per GPU in job 713 get several
    units on their heavy gates; the five that did not keep one unit."""
    for problem in (L2_59, L2_87, L2_100):
        native = trim.pilot.native_input_bytes(problem)
        assert native is not None and native < 600_000_000  # exec/1 gave them 1 unit
        assert memory.units_for(problem, "c", native) >= 4
        assert memory.units_for(problem, "A1", native) >= 4
        assert memory.units_for(problem, "a", native) >= 2
    for problem in (L1_10, L2_95, "L2/77_ConvTranspose3d_Scale_BatchNorm_GlobalAvgPool"):
        native = trim.pilot.native_input_bytes(problem)
        for gate in trim.SCORING_GATES:
            assert memory.units_for(problem, gate, native) == 1, (problem, gate)


def test_units_never_below_the_registered_floor_and_never_above_capacity() -> None:
    native = trim.pilot.native_input_bytes(L1_19)  # 6.4 GB: exclusive under exec/1
    assert memory.units_for(L1_19, "a", native) == 12
    assert memory.floor_units(700_000_000) == 3 and memory.floor_units(None) == 12
    # a problem missing from the table runs alone
    assert memory.units_for("L9/1_Missing", "a", 1000, entries={}) == 12
    assert memory.items_per_gpu(5) == 2 and memory.items_per_gpu(1) == 12


def test_peak_estimate_profiles_and_measured_override() -> None:
    entry = {
        "params_bytes": 1_000_000_000,
        "native": {"input_bytes": 100, "output_bytes": 200, "max_activation_bytes": 300},
        "all_configs": {"input_bytes": 1000, "output_bytes": 2000, "max_activation_bytes": 3000},
    }
    entries = {"P": entry}
    policy = memory.POLICY
    heavy = memory.estimated_peak_bytes("P", "c", entries=entries)
    light = memory.estimated_peak_bytes("P", "a", entries=entries)
    assert heavy == (
        policy["context_bytes"] + 5 * 1_000_000_000 + 3 * 1000 + 4 * 3000 + 4 * 2000 + 5 * 3000
    )
    assert light == (
        policy["context_bytes"] + 4 * 1_000_000_000 + 2 * 100 + 2 * 300 + 3 * 200 + 5 * 300
    )
    assert memory.profile_of("A4_sanitizer") == "variants-fp32"
    assert memory.profile_of("c1_kbv_native") == "variants-fp64"  # unknown: conservative
    measured = {"P|c": 2e9, "P": 1e9}
    assert memory.estimated_peak_bytes("P", "c", entries=entries, measured=measured) == int(
        2e9 * 1.25
    ) + int(policy["context_bytes"])
    assert memory.estimated_peak_bytes("P", "A2", entries=entries, measured=measured) == int(
        1e9 * 1.25
    ) + int(policy["context_bytes"])
    records = [
        {"problem_id": "P", "gate": "c", "peak_reserved_bytes": 5},
        {"problem_id": "P", "gate": "c", "peak_reserved_bytes": 9},
        {"problem_id": "P", "gate": "a", "peak_reserved_bytes": None},
    ]
    assert memory.measured_peaks(records) == {"P|c": 9.0}


def test_memory_table_is_current_and_covers_every_problem() -> None:
    table = memory.table()
    assert table["schema"] == memory.TABLE_SCHEMA
    manifest = json.loads((ROOT / "harness/q1/data/shape_manifest.json").read_text())
    assert set(table["problems"]) == set(manifest["problems"])
    for path, digest in table["generator_sha256"].items():
        from harness.q1.schema import sha256_file

        assert sha256_file(ROOT / path) == digest, f"{path} changed: rebuild the memory table"
    # the meta-device facts the review measured (finding 1)
    assert table["problems"][L2_59]["params_bytes"] > 4e9
    assert table["problems"][L2_100]["native"]["output_bytes"] > 3e9


def test_plan_items_carry_units_and_estimates_without_changing_order() -> None:
    from harness.q1.trim import KernelRecord

    records = [
        KernelRecord("s-a", "/a.py", L1_10, "substrate", half="evaluation", unit="u1"),
        KernelRecord("s-b", "/b.py", L2_59, "substrate", half="evaluation", unit="u2"),
        KernelRecord("s-c", "/c.py", L1_19, "substrate", half="evaluation", unit="u3"),
    ]
    rule = {**trim.TRIM_RULE, "frr_min_units": 3, "frr_margin_units": 0}
    record = trim.plan(records, rule=rule, exposed={})
    items = record["items"]
    assert record["execution_policy"]["name"] == memory.POLICY_VERSION
    assert record["memory_table_sha256"] and record["measured_memory_sha256"] is None
    by = {(i["kernel_id"], i["gate"]): i for i in items}
    assert by[("s-a", "c")]["units"] == 1 and by[("s-b", "c")]["units"] >= 4
    assert by[("s-c", "a")]["units"] == 12
    assert all(i["memory_bytes"] for i in items)
    # the order still follows the exec/1 class: shared problems before exclusive ones
    order = [i["kernel_id"] for i in items if i["bucket"] == "P1"]
    assert order.index("s-b") < order.index("s-c")
    measured = trim.plan(records, rule=rule, exposed={}, measured={f"{L2_59}|c": 1e9})
    by_m = {(i["kernel_id"], i["gate"]): i for i in measured["items"]}
    assert by_m[("s-b", "c")]["units"] == 1
    assert measured["plan_sha256"] != record["plan_sha256"]
    assert [i["kernel_id"] for i in measured["items"]] == [i["kernel_id"] for i in items]


def test_stage0_spend_is_read_from_the_ledger() -> None:
    state = json.loads((ROOT / "program/state.json").read_text())
    spent = trim.stage0_spent_gpu_hours(state["gpu_hours_ledger"])
    assert spent == pytest.approx(0.8989 + 0.33)
    assert trim.stage0_spent_gpu_hours([{"experiment": "q2-x", "gpu_hours": 9}]) == 0.0


# --- markers --------------------------------------------------------------------------


def test_one_resource_marker_list_for_runner_and_store() -> None:
    assert runner.OOM_MARKERS is faults.RESOURCE_MARKERS
    assert refstore.RESOURCE_MARKERS is faults.RESOURCE_MARKERS

    def row(**details: object) -> dict:
        return {"verdict": "error", "details": details}

    for text in (
        "RuntimeError: CUDA error: CUBLAS_STATUS_ALLOC_FAILED when calling cublasCreate",
        "cuDNN error: CUDNN_STATUS_INTERNAL_ERROR",
        "RuntimeError: Unable to find a valid cuDNN algorithm to run convolution",
        "torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 2.00 GiB",
    ):
        assert contention_failure([row(error=text)]) == "oom-shared", text
        assert refstore.resource_failure(RuntimeError(text))
    assert contention_failure([row(error="ValueError: shape mismatch")]) is None
    assert refstore.resource_failure(MemoryError())


def test_a5_na_reasons_reach_the_contention_rule() -> None:
    """A5's ``na`` checks keep the reference's exception text (finding 1)."""
    checks = [
        {
            "check": "EXC-01",
            "status": "na",
            "failures": [],
            "na_reasons": ["nan: reference raised OutOfMemoryError: CUDA out of memory."],
        }
    ]
    assert contention_failure([{"verdict": "error", "details": {"checks": checks}}]) == (
        "oom-shared"
    )


# --- memory guard and device share ----------------------------------------------------


def test_memory_guard_admission_rule() -> None:
    readings = {"cuda:0": (10, 100)}
    guard = MemoryGuard(60, probe=lambda slot: readings.get(slot), ttl=0)
    assert guard.admits("cuda:0", 40, reserved=20)  # max(10, 20) + 40 <= 60
    assert not guard.admits("cuda:0", 45, reserved=20)
    readings["cuda:0"] = (50, 100)  # more is used than this runner's estimates
    assert not guard.admits("cuda:0", 15, reserved=20)
    assert guard.admits("cpu", 10**12, reserved=0)
    unreadable = MemoryGuard(60, probe=lambda slot: None, ttl=0)
    assert unreadable.admits("cuda:0", 10**12, reserved=0) and unreadable.unreadable == 1


def test_device_share_waits_for_memory_but_never_deadlocks() -> None:
    used = {"value": 0}
    guard = MemoryGuard(100, probe=lambda slot: (used["value"], 200), ttl=0)
    share = DeviceShare(12, slot="cuda:0", guard=guard)
    stop = threading.Event()
    # nothing of this runner is running: admitted whatever the device reports
    used["value"] = 99
    assert share.acquire(False, stop, units=1, memory_bytes=90)
    got: list[float] = []

    def second() -> None:
        assert share.acquire(False, stop, units=1, memory_bytes=30)
        got.append(time.monotonic())

    thread = threading.Thread(target=second)
    thread.start()
    time.sleep(0.8)
    assert not got  # 90 reserved + 30 > 100 while the first item runs
    released = time.monotonic()
    share.release(False, 1, 90)
    thread.join(5)
    assert got and got[0] >= released
    assert share.guard_waits >= 1
    share.release(False, 1, 30)


def test_retired_device_admits_nothing() -> None:
    share = DeviceShare(4, slot="cuda:0")
    share.retire("gpu-health-fault")
    assert not share.acquire(False, threading.Event(), units=1)
    share.retire("other")
    assert share.retired == "gpu-health-fault"


# --- health check ------------------------------------------------------------------------


def test_health_classification() -> None:
    assert classify_health(0, "").ok
    oom = classify_health(1, "torch.OutOfMemoryError: CUDA out of memory. Tried to allocate")
    assert oom.kind == "allocation"
    assert classify_health(1, "RuntimeError: CUDA error: CUBLAS_STATUS_ALLOC_FAILED").kind == (
        "allocation"
    )
    fault = classify_health(1, "RuntimeError: CUDA error: uncorrectable ECC error encountered")
    assert fault.kind == "fault" and "uncorrectable ecc" in fault.detail
    assert classify_health(None, "", timed_out=True).kind == "fault"


def _health_script(tmp_path: Path, outcomes: list[str]) -> list[str]:
    """A fake health check: the n-th call prints and exits as ``outcomes[n]`` (the last
    one repeats) and logs the call time."""
    state = tmp_path / "health-calls.txt"
    script = tmp_path / "health.py"
    script.write_text(
        "import sys, time, pathlib\n"
        f"state = pathlib.Path({str(state)!r})\n"
        "calls = state.read_text().splitlines() if state.exists() else []\n"
        f"outcomes = {outcomes!r}\n"
        "kind = outcomes[min(len(calls), len(outcomes) - 1)]\n"
        "state.write_text('\\n'.join([*calls, repr(time.time())]) + '\\n')\n"
        "if kind == 'ok':\n    sys.exit(0)\n"
        "if kind == 'oom':\n"
        "    print('torch.OutOfMemoryError: CUDA out of memory. Tried to allocate 20.00 MiB')\n"
        "    sys.exit(1)\n"
        "print('RuntimeError: CUDA error: uncorrectable ECC error encountered')\n"
        "sys.exit(1)\n"
    )
    return [sys.executable, str(script)]


class FakeRunner(Runner):
    """Runs items without a worker: ``plan[(key, attempt)]`` is ``crash-oom`` (a
    worker that died with a CUDA out-of-memory error in its log: the runner's own
    crash row, health check due), ``crash`` (died, no resource text) or ``accept``."""

    def __init__(self, config: RunnerConfig, plan: dict, seconds: float = 0.3) -> None:
        super().__init__(config)
        self.plan = plan
        self.seconds = seconds
        self.spans: list[tuple[str, float, float]] = []
        self._spans_lock = threading.Lock()

    def execute(self, item: WorkItem, attempt: int, slot: str) -> tuple[list[dict], bool]:
        start = time.time()
        time.sleep(self.seconds)
        kind = self.plan.get((item.key, attempt), "accept")
        end = time.time()
        with self._spans_lock:
            self.spans.append((item.key, start, end))
        crashed = kind.startswith("crash")
        details = {
            "item_key": item.key,
            "item_final": True,
            "item_started_at": start,
            "item_ended_at": end,
            "item_exclusive": item.exclusive,
            "slot": slot,
        }
        if crashed:
            details.update(
                reason="worker-crashed",
                phase="correctness",
                log_tail="torch.OutOfMemoryError: CUDA out of memory."
                if kind == "crash-oom"
                else "",
            )
        row = make_verdict_row(
            kernel_id=item.kernel_id,
            gate=item.gate,
            config_id=f"item/seed-{item.seed}",
            verdict="reject" if crashed else "accept",
            tf32_policy="not-applicable",
            gpu_seconds=end - start,
            wall_seconds=end - start,
            details=details,
            seed=item.seed,
            run_id=self.config.run_id,
            attempt=attempt,
            code_sha256="0" * 64,
        )
        return [row], crashed


def _items(n: int) -> list[WorkItem]:
    return [WorkItem(f"k{i}", "", L1_10, "a", units=1) for i in range(n)]


def _config(tmp_path: Path, command: list[str], slots: int = 3, **extra: object) -> RunnerConfig:
    return RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        slots=["cuda:0"] * slots,
        health_command=command,
        health_retry_delays=(0.05, 0.05),
        workdir=tmp_path,
        **extra,
    )


def test_contention_never_retires_a_healthy_slot(tmp_path: Path) -> None:
    """Job 713: a crash under memory pressure, then a health check that cannot get
    memory. The slot drains its device, the check passes alone, no slot stops, and the
    crashed item (its log shows an out-of-memory error) runs again alone."""
    items = _items(6)
    plan = {(items[0].key, 1): "crash-oom"}
    config = _config(tmp_path, _health_script(tmp_path, ["oom", "ok"]))
    fake = FakeRunner(config, plan)
    summary = fake.run(items)
    assert summary["retired_slots"] == [] and summary["retired_devices"] == {}
    assert summary["health_recovered_alone"] == 1
    assert summary["left_in_queue"] == 0
    rows = Journal(config.journal_path).final_rows()
    final = {r["details"]["item_key"]: r for r in rows}
    assert len(final) == 6 and all(r["verdict"] == "accept" for r in final.values())
    assert final[items[0].key]["attempt"] == 2  # retried alone after the shared crash
    (event,) = summary["health_events"]
    assert event["first"] == "allocation" and event["alone"] == "ok"
    # The repeated check ran alone: no item ran while it did.
    calls = [
        float(x) for x in (tmp_path / "health-calls.txt").read_text().splitlines() if x.strip()
    ]
    assert len(calls) == 2
    alone_at = calls[1]
    assert not [s for s in fake.spans if s[1] < alone_at < s[2]]


def test_allocation_failure_alone_stops_the_device_as_memory_held(tmp_path: Path) -> None:
    items = _items(8)
    plan = {(items[0].key, 1): "crash"}
    config = _config(tmp_path, _health_script(tmp_path, ["oom"]))
    summary = FakeRunner(config, plan).run(items)
    assert set(summary["retired_devices"].values()) == {"gpu-memory-held"}
    assert summary["left_in_queue"] > 0  # unstarted items wait for the next job
    rows = Journal(config.journal_path).final_rows()
    crashed = [r for r in Journal(config.journal_path).read()[0] if r["kernel_id"] == "k0"]
    assert crashed[0]["details"]["reason"] == "infra_failure-gpu-health-check"
    assert crashed[0]["details"]["health"]["kind"] == "allocation"
    assert not crashed[0]["details"]["item_final"]  # an infrastructure failure: retried later
    assert all(r["verdict"] == "accept" for r in rows if r["kernel_id"] != "k0")


def test_a_fault_alone_stops_the_device(tmp_path: Path) -> None:
    items = _items(5)
    plan = {(items[0].key, 1): "crash"}
    config = _config(tmp_path, _health_script(tmp_path, ["fault"]))
    summary = FakeRunner(config, plan).run(items)
    assert set(summary["retired_devices"].values()) == {"gpu-health-fault"}
    assert summary["health_failed_alone"] == 1


def test_a_crash_without_resource_text_keeps_its_verdict(tmp_path: Path) -> None:
    """A candidate that crashes the worker after loading is rejected (section 10) when
    the device is healthy: the health check passes at once, nothing is retried."""
    items = _items(2)
    plan = {(items[0].key, 1): "crash"}
    config = _config(tmp_path, _health_script(tmp_path, ["ok"]))
    summary = FakeRunner(config, plan).run(items)
    assert summary["retired_slots"] == [] and not summary["health_events"]
    final = {r["kernel_id"]: r for r in Journal(config.journal_path).final_rows()}
    assert final["k0"]["verdict"] == "reject" and final["k0"]["attempt"] == 1


def test_on_done_sees_every_item_once_with_its_rows(tmp_path: Path) -> None:
    seen: list[tuple[str, int | None]] = []
    lock = threading.Lock()

    def hook(item: WorkItem, rows: list[dict] | None) -> None:
        with lock:
            seen.append((item.key, None if rows is None else rows[-1]["attempt"]))

    items = _items(4)
    plan = {(items[1].key, 1): "crash-oom"}
    config = _config(tmp_path, _health_script(tmp_path, ["ok"]), on_done=hook)
    FakeRunner(config, plan, seconds=0.05).run(items)
    assert sorted(seen) == sorted([(i.key, 2 if i is items[1] else 1) for i in items])


def test_memory_records_are_appended_beside_the_journal(tmp_path: Path) -> None:
    config = RunnerConfig(journal_path=tmp_path / "journal.jsonl", workdir=tmp_path)
    work = tmp_path / "item"
    work.mkdir()
    (work / "memory.json").write_text(json.dumps({"peak_reserved_bytes": 123}))
    item = WorkItem("k", "", L1_10, "c", units=2, memory_bytes=456)
    Runner(config)._record_memory(item, 1, "cuda:0", work)
    (record,) = [json.loads(x) for x in (tmp_path / "memory.jsonl").read_text().splitlines()]
    assert record["peak_reserved_bytes"] == 123 and record["memory_bytes_estimate"] == 456
    assert memory.measured_peaks([record]) == {f"{L1_10}|c": 123.0}


# --- reference-store schedule, caps and janitor ------------------------------------------


def _consumer(kernel: str, gate: str, problem: str) -> dict:
    from dataclasses import asdict

    return asdict(WorkItem(kernel, f"/k/{kernel}.py", problem, gate, units=2, memory_bytes=7))


def test_gate_a_is_never_a_store_consumer() -> None:
    assert set(refstore.CONSUMERS) == {"c", "A1", "A2", "A3", "A5"}
    items = [_consumer(k, g, L1_10) for k in ("k1", "k2") for g in ("a", "a_head_1e-4", "c")]
    out = refschedule.with_references(items, root="/s")
    assert [i["gate"] for i in out if refstore.is_reference_gate(i["gate"])] == ["ref_c"]
    assert all(not i.get("requires") for i in out if i["gate"].startswith("a"))


def test_entry_cap_sends_huge_groups_inline_and_footprint_is_estimated() -> None:
    items = [_consumer(k, g, p) for p in (L1_10, L2_100) for k in ("k1", "k2") for g in ("c", "A1")]
    over: list[dict] = []
    estimates: dict = {}
    out = refschedule.with_references(
        items,
        root="/s",
        store_cap_bytes=refstore.STORE_CAP_BYTES,
        over_cap=over,
        estimates=estimates,
    )
    refs = [i for i in out if refstore.is_reference_gate(i["gate"])]
    # L2/100's gate (c) entry (about 100 GB of fp32 outputs) is over the 50 GB cap
    assert [(o["problem_id"], o["channel"]) for o in over] == [(L2_100, "c")]
    assert {(r["problem_id"], r["gate"]) for r in refs} == {
        (L1_10, "ref_c"),
        (L1_10, "ref_A1"),
        (L2_100, "ref_A1"),
    }
    assert all(r["options"][refstore.CAP_OPTION] == refstore.STORE_CAP_BYTES for r in refs)
    assert all(r["memory_bytes"] == 7 and r["units"] == 2 for r in refs)
    assert set(estimates) == {f"{r['kernel_id']}|{r['gate']}|seed-42" for r in refs}
    facts = refschedule.footprint(out, estimates)
    assert facts["entries_bytes_estimate"] == sum(estimates.values())
    assert 0 < facts["peak_live_bytes_estimate"] <= facts["entries_bytes_estimate"]
    WorkItem(**out[0])  # scheduled items are WorkItem fields only


def test_janitor_deletes_an_entry_after_its_last_consumer(tmp_path: Path) -> None:
    from scripts.run_q1_stage0 import StoreJanitor

    entry = tmp_path / "c" / "key"
    entry.mkdir(parents=True)
    (entry / "entry.json").write_text("{}")
    (entry / "draw-000.pt").write_bytes(b"x" * 100)
    ref = WorkItem("reference.p", "", "p", "ref_c")
    consumers = [WorkItem(f"k{i}", "", "p", "c", requires=[ref.key]) for i in range(2)]
    janitor = StoreJanitor([ref, *consumers])
    janitor(ref, [{"details": {"entry_dir": str(entry)}}])
    janitor(consumers[0], [{}])
    assert (entry / "draw-000.pt").exists()
    janitor(consumers[1], None)  # deferred or cut also counts as having left
    assert not (entry / "draw-000.pt").exists() and (entry / "entry.json").exists()
    assert janitor.deleted == 1 and janitor.freed_bytes == 100


# --- cost card ---------------------------------------------------------------------------


def test_concurrency_multiplier() -> None:
    f = 0.45
    assert cost_card.concurrency_multiplier(1, f) == f
    assert cost_card.concurrency_multiplier(3, f) == pytest.approx(1.0)  # 4 per GPU
    assert cost_card.concurrency_multiplier(2, f) == pytest.approx(f + (1 - f) * 0.5)
    assert cost_card.concurrency_multiplier(5, f) == pytest.approx(2.0)  # 2 per GPU: 4/2
    assert cost_card.concurrency_multiplier(12, f) == pytest.approx(4.0)  # alone


def test_store_model_without_gate_a() -> None:
    pairs = [
        {"gate": g, "problem_id": L1_10, "inline": 2.0, "store": 1.0, "same_mode": True}
        for g in ("a", "c", "A1")
    ]
    refs = [
        {"gate": g, "problem_id": L1_10, "gpu_seconds": 1.0} for g in ("ref_a", "ref_c", "ref_A1")
    ]
    model = cost_card.fit_store_model(pairs, refs, ratio_mode="constant")
    assert set(model.constant_ratios) == {"c", "A1"} and "ref_a" not in model.reference_fits
    old = cost_card.fit_store_model(
        pairs, refs, ratio_mode="constant", consumers=cost_card.STORE_CONSUMER_GATES_REPILOT
    )
    assert "a" in old.constant_ratios and "ref_a" in old.reference_fits
