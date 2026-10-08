"""Reference store (decision D31): keys, entries, fallbacks, side-effect probe,
scheduling and the runner's requirements. CPU only (torch and triton required for
the runner and probe tests; the scheduling tests are pure Python)."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict
from pathlib import Path

import pytest

os.environ.setdefault("TRITON_INTERPRET", "1")
torch = pytest.importorskip("torch")
pytest.importorskip("triton")
if torch.cuda.is_available():  # pragma: no cover - CPU-only fixtures
    pytest.skip("fixtures are CPU-only", allow_module_level=True)

from harness.q1 import doctor_fixtures as fx  # noqa: E402
from harness.q1 import refschedule, refstore  # noqa: E402
from harness.q1.journal import Journal, item_key  # noqa: E402
from harness.q1.runner import ReadyQueue, Runner, RunnerConfig, WorkItem  # noqa: E402

CPU = torch.device("cpu")
RELU = "L1/9001_SyntheticReLU"


def _payload(**params: object) -> dict:
    return refstore.key_payload(
        "A1",
        problem_id=RELU,
        problem_source=fx.PROBLEMS[RELU],
        seed=42,
        device_type="cpu",
        params=params or {"draws": 5},
    )


def test_key_binds_source_seed_channel_params_and_code() -> None:
    base = _payload()
    key = refstore.key_of(base)
    assert key == refstore.key_of(_payload())
    assert key != refstore.key_of({**base, "seed": 43})
    assert key != refstore.key_of({**base, "problem_sha256": "0" * 64})
    assert key != refstore.key_of(_payload(draws=4))
    assert key != refstore.key_of({**base, "code_sha256": "1" * 64})
    assert base["code_sha256"] == refstore.code_sha256("A1")
    assert refstore.code_sha256("a") != refstore.code_sha256("A1")


def _built(problems: list[str] | None = None) -> refstore.Built:
    return refstore.Built(
        draws=[
            refstore.Draw({"kind": "ok", "n": 0}, torch.arange(4.0)),
            refstore.Draw({"kind": "raised", "error": {"error_name": "x.Y", "error": "Y: no"}}),
        ],
        problems=list(problems or []),
        facts=refstore.environment_facts(),
    )


def test_write_lookup_take_roundtrip(tmp_path: Path) -> None:
    payload = _payload()
    manifest = refstore.write_entry(tmp_path, payload, _built())
    assert manifest["usable"] and manifest["draws"][0]["file"] == "draw-000.pt"
    refstore.USES.clear()
    entry = refstore.lookup(tmp_path, payload, draws=2)
    assert entry is not None and refstore.USES[-1]["used"]
    first = entry.take(0, CPU)
    assert first.kind == "ok" and torch.equal(first.value, torch.arange(4.0))
    second = entry.take(1, CPU)
    assert second.kind == "raised" and second.error["error_name"] == "x.Y"
    # A second writer keeps the first entry.
    again = refstore.write_entry(tmp_path, payload, _built(["other"]))
    assert again["usable"] and again["written_at"] == manifest["written_at"]
    assert not list((tmp_path / "A1").glob(".*.tmp"))


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("unusable", "entry-unusable"),
        ("missing", "no-entry"),
        ("short", "entry-incomplete"),
        ("truncated", "entry-incomplete"),
        ("payload", "payload-mismatch"),
    ],
)
def test_lookup_refuses_entries_it_cannot_trust(tmp_path: Path, change: str, reason: str) -> None:
    payload = _payload()
    if change != "missing":
        refstore.write_entry(tmp_path, payload, _built(["x"] if change == "unusable" else None))
    path = refstore.entry_dir(tmp_path, "A1", refstore.key_of(payload))
    if change == "truncated":
        data = (path / "draw-000.pt").read_bytes()
        (path / "draw-000.pt").write_bytes(data[:-10])
    if change == "payload":
        manifest = json.loads((path / "entry.json").read_text())
        manifest["payload"]["seed"] = 43
        (path / "entry.json").write_text(json.dumps(manifest))
    refstore.USES.clear()
    expected = 3 if change == "short" else 2
    assert refstore.lookup(tmp_path, payload, draws=expected) is None
    assert refstore.USES[-1] == {
        **refstore.USES[-1],
        "used": False,
        "reason": reason,
    }


def test_short_entry_is_complete_only_when_it_ends_at_a_raise(tmp_path: Path) -> None:
    payload = _payload()
    refstore.write_entry(tmp_path, payload, _built())
    assert refstore.lookup(tmp_path, payload, draws=5) is None
    assert refstore.lookup(tmp_path, payload, draws=5, ends_at_raise=True) is not None


def test_switch_change_means_inline_from_that_draw(tmp_path: Path) -> None:
    payload = _payload()
    refstore.write_entry(tmp_path, payload, _built())
    refstore.USES.clear()
    entry = refstore.lookup(tmp_path, payload, draws=2)
    old = torch.backends.cudnn.benchmark
    try:
        torch.backends.cudnn.benchmark = not old
        assert entry.take(0, CPU) is None
    finally:
        torch.backends.cudnn.benchmark = old
    assert refstore.USES[-1]["inline_from_draw"] == 0
    assert refstore.USES[-1]["inline_reason"] == "switches-changed"
    # A file that disappeared is a store fault: inline from there, never a verdict.
    (entry.path / "draw-000.pt").unlink()
    assert entry.take(0, CPU) is None
    assert refstore.USES[-1]["inline_reason"].startswith("read-failed")


def test_probe_sees_input_writes_rng_use_and_aliasing() -> None:
    x = torch.rand(8)
    problems: list[str] = []
    refstore.checked_call(lambda: x * 2, [x], CPU, problems)
    assert problems == []
    refstore.checked_call(lambda: x.mul_(2), [x], CPU, problems)
    assert "reference-mutated-input-0" in problems
    assert "reference-output-aliases-input" in problems
    problems.clear()
    refstore.checked_call(lambda: x + torch.rand(8), [x], CPU, problems)
    assert problems == ["reference-changed-rng-state"]
    problems.clear()
    refstore.checked_call(lambda: x.view(2, 4), [x], CPU, problems)
    assert problems == ["reference-output-aliases-input"]
    problems.clear()
    refstore.checked_call(lambda: {"a": x * 2}, [x], CPU, problems)
    assert problems == ["reference-output-not-storable"]


def test_resource_failures_are_never_stored_as_outcomes() -> None:
    assert refstore.resource_failure(RuntimeError("CUDA out of memory. Tried to allocate"))
    assert refstore.resource_failure(MemoryError())
    assert not refstore.resource_failure(ValueError("shape mismatch"))


# --- scheduling ---------------------------------------------------------------------


def _consumer(kernel: str, gate: str, problem: str = RELU, seed: int = 42) -> dict:
    return asdict(
        WorkItem(
            kernel_id=kernel,
            kernel_path=f"/k/{kernel}.py",
            problem_id=problem,
            gate=gate,
            seed=seed,
            units=3,
            timeouts={"compile": 130.0, "correctness": 230.0, "timing": 320.0},
        )
    )


def test_with_references_groups_places_and_requires() -> None:
    items = [
        _consumer("k1", "a"),
        _consumer("k1", "a_head_1e-4"),
        _consumer("k1", "b1"),
        _consumer("k1", "c"),
        _consumer("k2", "a_1e-3"),
        _consumer("k2", "c"),
        _consumer("k2", "A1"),
        _consumer("k3", "A1", seed=43),
        _consumer("solo", "A2", problem="L1/9002_SyntheticRowSum"),
    ]
    out = refschedule.with_references(items, root="/store")
    gates = [i["gate"] for i in out]
    # ref_a before k1|a, ref_c before k1|c; a_head, A1@43 and the row-sum A2 have
    # one kernel each (inline); A1@42 has only k2 (inline as well)
    assert gates == [
        "ref_a",
        "a",
        "a_head_1e-4",
        "b1",
        "ref_c",
        "c",
        "a_1e-3",
        "c",
        "A1",
        "A1",
        "A2",
    ]
    ref_a = out[0]
    assert ref_a["kernel_id"] == "reference.L1-9001_SyntheticReLU"
    assert ref_a["journal"] == refstore.REFERENCE_JOURNAL and ref_a["units"] == 3
    assert ref_a["timeouts"]["compile"] == 130.0 + 230.0
    assert ref_a["options"] == {refstore.OPTION: "/store"}
    by_key = {item_key(i["kernel_id"], i["gate"], i["seed"]): i for i in out}
    assert by_key["k1|a|seed-42"]["requires"] == ["reference.L1-9001_SyntheticReLU|ref_a|seed-42"]
    assert by_key["k2|a_1e-3|seed-42"]["options"][refstore.OPTION] == "/store"
    assert not by_key["k1|b1|seed-42"].get("requires")
    assert not by_key["k2|A1|seed-42"].get("requires")
    assert refstore.OPTION not in by_key["solo|A2|seed-42"]["options"]
    assert refschedule.summary(out) == {
        "reference_items": {"ref_a": 1, "ref_c": 1},
        "consumers_with_store": 4,
    }


def test_groups_split_by_problem_source_and_entry_options() -> None:
    a = {**_consumer("k1", "c"), "problem_source_path": "/p/one.py"}
    b = {**_consumer("k2", "c"), "problem_source_path": "/p/one.py"}
    c = {**_consumer("k3", "c"), "problem_source_path": "/p/two.py"}
    d = {
        **_consumer("k4", "c"),
        "problem_source_path": "/p/two.py",
        "options": {"manifest_path": "m"},
    }
    out = refschedule.with_references([a, b, c, d], root="/s")
    refs = [i for i in out if refstore.is_reference_gate(i["gate"])]
    assert len(refs) == 1 and refs[0]["problem_source_path"] == "/p/one.py"
    assert refs[0]["kernel_id"].startswith("reference.L1-9001_SyntheticReLU.")


# --- runner requirements ------------------------------------------------------------


def test_ready_queue_skips_blocked_items_and_waits() -> None:
    pending = {"r|ref_c|seed-42", "x|c|seed-42", "y|a|seed-42"}
    stopped = threading.Event()
    queue = ReadyQueue(pending, stopped)
    blocked = WorkItem("x", "", RELU, "c", requires=["r|ref_c|seed-42"])
    free = WorkItem("y", "", RELU, "a")
    queue.put((blocked, 1))
    queue.put((free, 1))
    assert queue.get()[0].key == "y|a|seed-42"
    started = time.monotonic()

    def release() -> None:
        time.sleep(0.3)
        pending.discard("r|ref_c|seed-42")
        queue.notify()

    threading.Thread(target=release).start()
    assert queue.get()[0].key == "x|c|seed-42"
    assert time.monotonic() - started >= 0.25
    assert queue.get() is None  # empty
    queue.put((blocked, 1))
    pending.add("r|ref_c|seed-42")
    stopped.set()
    assert queue.get() is None  # stopped while blocked


def _doctor_items(tmp_path: Path, names: list[str], gates: tuple[str, ...]) -> list[WorkItem]:
    items = []
    for name in names:
        spec = fx.KERNELS[name]
        problem_id = str(spec["problem"])
        problem = tmp_path / "problem.py"
        problem.write_text(fx.PROBLEMS[problem_id])
        kernel = tmp_path / f"{name}.py"
        kernel.write_text(str(spec["source"]))
        items += [
            WorkItem(
                kernel_id=f"t-{name}",
                kernel_path=str(kernel),
                problem_id=problem_id,
                gate=gate,
                problem_source_path=str(problem),
            )
            for gate in gates
        ]
    return items


def test_runner_runs_references_first_and_keeps_them_out_of_the_journal(tmp_path: Path) -> None:
    items = _doctor_items(tmp_path, ["relu_correct", "relu_removed"], ("a", "A1"))
    store = tmp_path / "store"
    scheduled = [
        WorkItem(**e)
        for e in refschedule.with_references([asdict(i) for i in items], root=str(store))
    ]
    assert [i.gate for i in scheduled][:2] == ["ref_a", "a"]
    (tmp_path / "w").mkdir()
    config = RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        slots=["cpu"] * 4,
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=tmp_path / "w",
    )
    summary = Runner(config).run(scheduled)
    assert summary["left_in_queue"] == 0
    main = Journal(config.journal_path).final_rows()
    refs = Journal(tmp_path / refstore.REFERENCE_JOURNAL).final_rows()
    assert {r["gate"] for r in refs} == {"ref_a", "ref_A1"}
    assert all(r["verdict"] == "accept" for r in refs)
    assert not any(refstore.is_reference_gate(r["gate"]) for r in main)
    # every consumer started after its reference item ended
    ended = {r["details"]["item_key"]: r["details"]["item_ended_at"] for r in refs}
    for row in main:
        needed = next(i.requires for i in scheduled if i.key == row["details"]["item_key"])
        assert all(row["details"]["item_started_at"] >= ended[k] - 1e-3 for k in needed)
    uses = refstore.read_uses(store)
    assert len(uses) == 4 and all(lk["used"] for u in uses for lk in u["lookups"])
    # A resumed run skips the finished reference items too.
    again = Runner(config).run(scheduled)
    assert again["run"] == 0 and again["skipped"] == len(scheduled)


def test_a_failed_reference_item_does_not_block_its_consumers(tmp_path: Path) -> None:
    items = _doctor_items(tmp_path, ["relu_correct", "relu_removed"], ("a",))
    store = tmp_path / "store"
    scheduled = [
        WorkItem(**e)
        for e in refschedule.with_references([asdict(i) for i in items], root=str(store))
    ]
    # Break the reference item: its problem source does not exist.
    ref = scheduled[0]
    scheduled[0] = WorkItem(**{**asdict(ref), "problem_source_path": str(tmp_path / "nope.py")})
    (tmp_path / "w").mkdir()
    config = RunnerConfig(
        journal_path=tmp_path / "journal.jsonl",
        slots=["cpu"] * 2,
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=tmp_path / "w",
    )
    summary = Runner(config).run(scheduled)
    assert summary["left_in_queue"] == 0
    verdicts = {r["kernel_id"]: r["verdict"] for r in Journal(config.journal_path).final_rows()}
    # relu_removed is the identity on torch.rand inputs, which gate (a) accepts
    assert verdicts == {"t-relu_correct": "accept", "t-relu_removed": "accept"}
    reasons = {lk["reason"] for u in refstore.read_uses(store) for lk in u["lookups"]}
    assert reasons == {"no-entry"}
