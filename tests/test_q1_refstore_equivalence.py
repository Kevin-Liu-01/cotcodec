"""Decision D31: the reference store leaves every verdict row unchanged (synthetic corpus).

The CPU doctor's synthetic corpus (``harness/q1/doctor_fixtures.py``: four
problems, 22 candidates with known verdicts, integer outputs, crashes, a hang,
refusals, uninitialised memory and in-place writes) runs through the real
runner twice: inline (every item computes its own references, the path every
pilot verdict came from) and with the reference store (one reference item per
problem and channel, consumers read its entry). The final verdict rows must be
identical except for timing and run-identity fields, every consumer must have
used an entry, and the reference items must leave the scoring journal alone.
The committed integration fixtures are compared the same way in
``tests/test_q1_integration_cpu.py::test_reference_store_rows_equal_inline_rows``.

CPU only, Triton under ``TRITON_INTERPRET=1`` (decisions D3, D7, D12).
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import pytest

os.environ.setdefault("TRITON_INTERPRET", "1")
torch = pytest.importorskip("torch")
pytest.importorskip("triton")
if torch.cuda.is_available():  # pragma: no cover - CPU-only fixtures
    pytest.skip("the doctor fixtures are CPU-only", allow_module_level=True)

from harness.q1 import refschedule, refstore  # noqa: E402
from harness.q1.journal import Journal  # noqa: E402
from harness.q1.runner import Runner, RunnerConfig, WorkItem  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_q1_gate_doctor as doctor  # noqa: E402
from tests._q1_rows import (  # noqa: E402, F401 - re-exported for the integration test
    describe,
    differences,
    fails_dual_poison,
    normalized,
    row_index,
)


def run_items(items: list[WorkItem], base: Path, *, slots: int) -> dict:
    (base / "items").mkdir(parents=True)
    config = RunnerConfig(
        journal_path=base / "journal.jsonl",
        slots=["cpu"] * slots,
        timeouts=doctor.DOCTOR_TIMEOUTS,
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=base / "items",
    )
    summary = Runner(config).run(items)
    return {"summary": summary, "rows": Journal(config.journal_path).final_rows()}


def with_store(items: list[WorkItem], store: Path) -> list[WorkItem]:
    scheduled = refschedule.with_references([asdict(i) for i in items], root=str(store))
    return [
        WorkItem(**({**e, "journal": str(store / "references.jsonl")} if e.get("journal") else e))
        for e in scheduled
    ]


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict:
    base = tmp_path_factory.mktemp("q1-refstore-doctor")
    problem_paths, kernel_paths, manifest_path = doctor.build_corpus(base / "corpus")
    items = [
        item
        for item in doctor.work_items(problem_paths, kernel_paths, manifest_path)
        if item.gate != "timing"
    ]
    slots = min(16, os.cpu_count() or 2)
    inline = run_items(items, base / "inline", slots=slots)
    store = base / "store-root"
    scheduled = with_store(items, store)
    stored = run_items(scheduled, base / "store", slots=slots)
    return {
        "items": items,
        "scheduled": scheduled,
        "inline": inline,
        "store": stored,
        "store_root": store,
    }


def test_store_rows_equal_inline_rows(runs: dict) -> None:
    inline, stored = runs["inline"]["rows"], runs["store"]["rows"]
    assert len(inline) == len(stored) > 200
    poisoned = fails_dual_poison(inline)
    assert poisoned == fails_dual_poison(stored)
    assert poisoned == {"doctor-relu_empty_tail", "doctor-relu_nondeterministic"}
    diff = differences(inline, stored)
    outside = [d for d in diff if d["key"][0] not in poisoned]
    assert not outside, describe(outside)
    # The noise kernel's output depends on the RNG state at each call, which the
    # store leaves exactly as the inline references did: its rows are identical.
    assert not [d for d in diff if d["key"][0] == "doctor-relu_nondeterministic"]
    # A4 never reads a reference, yet even its rows differ for the kernel that reads
    # unwritten bytes (which subchecks catch it depends on the garbage): such rows are
    # not reproducible on the inline path either. Its A4 verdict (reject), and so every
    # audit tier, agrees.
    for d in diff:
        if d["key"][1].startswith("A4"):
            verdicts = [{json.loads(r)["verdict"] for r in d[side]} for side in ("inline", "store")]
            assert verdicts[0] == verdicts[1] == {"reject"}, d
    print(
        json.dumps(
            {
                "rows": len(inline),
                "identical": len(inline) - sum(len(d["inline"] or []) for d in diff),
                "differing_rows_of_relu_empty_tail": sorted(d["key"][1:3] for d in diff),
            }
        )
    )


def test_reference_items_ran_and_stayed_out_of_the_scoring_journal(runs: dict) -> None:
    refs = [i for i in runs["scheduled"] if refstore.is_reference_gate(i.gate)]
    # ReLU, row-sum and argmax have at least two kernels each (the cross-entropy
    # problem has one, so it computes inline): 3 problems x 5 channels (gate (a) never
    # reads the store)
    assert len(refs) == 15, Counter(i.gate for i in refs)
    assert {i.problem_id for i in refs} == {
        "L1/9001_SyntheticReLU",
        "L1/9002_SyntheticRowSum",
        "L1/9004_SyntheticArgmax",
    }
    assert not any(refstore.is_reference_gate(r["gate"]) for r in runs["store"]["rows"])
    ref_rows = Journal(runs["store_root"] / "references.jsonl").final_rows()
    assert len(ref_rows) == len(refs)
    # An entry is unusable only for a reason that leaves inline consumers unchanged
    # (a reference that raised or changed its inputs); never a store fault.
    unusable = [
        (r["kernel_id"], r["gate"], r["details"].get("problems"), r["details"].get("error"))
        for r in ref_rows
        if r["verdict"] != "accept"
    ]
    assert all(r[2] for r in unusable) and len(unusable) <= len(ref_rows) // 3, unusable
    summary = runs["store"]["summary"]
    assert summary["left_in_queue"] == 0 and summary["run"] >= len(runs["scheduled"])


def test_every_consumer_read_an_entry(runs: dict) -> None:
    uses = refstore.read_uses(runs["store_root"])
    consumers = [i for i in runs["scheduled"] if i.requires]
    by_key = {u["item_key"]: u for u in uses}
    # A consumer records its lookups only if its worker returned and it reached its
    # first reference: not a hang or crash (runner rows), a compile failure or a
    # failed static check, all of which end before any reference is read.
    early = {
        r["details"]["item_key"]
        for r in runs["store"]["rows"]
        if r["config_id"].startswith("item/")
        or r["details"].get("reason") in {"compile-failure", "static-check", "load-failure"}
    }
    missing = [i.key for i in consumers if i.key not in by_key and i.key not in early]
    assert not missing, missing[:5]
    assert len(by_key) >= 0.8 * len(consumers)
    fallbacks = [
        (u["item_key"], lookup)
        for u in uses
        for lookup in u["lookups"]
        if (not lookup.get("used") and lookup.get("reason") != "entry-unusable")
        or lookup.get("inline_from_draw") is not None
    ]
    # A consumer that crashed, hung or was rejected before its first reference
    # (compile failure, static check) never looks up; every lookup of a usable entry
    # used it for every draw (unusable entries: see the test above).
    assert not fallbacks, fallbacks[:5]
    channels = Counter(lookup["channel"] for u in uses for lookup in u["lookups"])
    assert set(channels) == set(refstore.CONSUMERS), channels


def test_a_missing_or_unusable_entry_means_inline(runs: dict, tmp_path: Path) -> None:
    """A consumer pointed at an empty store computes inline: same rows, recorded as such."""
    items = [i for i in runs["items"] if i.kernel_id == "doctor-relu_correct"]
    empty = tmp_path / "empty-store"
    pointed = [
        WorkItem(**{**asdict(i), "options": {**i.options, refstore.OPTION: str(empty)}})
        for i in items
    ]
    result = run_items(pointed, tmp_path / "run", slots=4)
    inline = [r for r in runs["inline"]["rows"] if r["kernel_id"] == "doctor-relu_correct"]
    assert not differences(inline, result["rows"])
    reasons = Counter(
        lookup["reason"] for u in refstore.read_uses(empty) for lookup in u["lookups"]
    )
    assert reasons and set(reasons) == {"no-entry"}, reasons
