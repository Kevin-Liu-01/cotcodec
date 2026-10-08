"""Reference store semantics after the D31 review (findings 1, 3, 4 and 5).

CPU only; torch required (no Triton: gate (c) and A5 with plain-PyTorch candidates
run in this process). Each case runs a gate inline and through the store and
compares the rows the way ``tests/test_q1_refstore_equivalence.py`` does.

- a reference that raises makes its entry unusable (no tensors), so consumers
  compute inline instead of turning every consumer into an ``error``;
- a resource failure in a reference call writes no entry and puts its text in
  the reference row, where the runner's contention rule finds it;
- gate (c): a candidate that flips a tracked switch mid-item makes the consumer
  fall back inline, after replaying the reference forwards the store skipped, so
  a stateful reference gives the inline rows;
- A5: a candidate that writes an integer input in place between checks makes
  the remaining reference calls inline (per-call input fingerprint);
- A5 ``na`` checks keep the reference's exception text;
- input fingerprints, the disk cap, and deleting an entry's tensors.
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
if torch.cuda.is_available():  # pragma: no cover - CPU-only fixtures
    pytest.skip("fixtures are CPU-only", allow_module_level=True)

from harness.q1 import refstore  # noqa: E402
from harness.q1.gates import gate_c  # noqa: E402
from harness.q1.runner import contention_failure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests._q1_rows import differences  # noqa: E402

CPU = torch.device("cpu")


def _problem(body: str, inputs: str, init: str = "[]") -> str:
    """A KernelBench-style problem file: ``Model`` with ``body``, ``get_inputs`` and
    ``get_init_inputs``."""
    model = textwrap.indent(textwrap.dedent(body).strip("\n"), "    ")
    return (
        "import torch\n"
        "import torch.nn as nn\n\n"
        "batch_size = 8\n"
        "dim = 16\n\n\n"
        f"class Model(nn.Module):\n{model}\n\n\n"
        f"def get_inputs():\n    return {inputs}\n\n\n"
        f"def get_init_inputs():\n    return {init}\n"
    )


STATEFUL = _problem(
    """
    def __init__(self):
        super().__init__()
        self.register_buffer("calls", torch.zeros(()))

    def forward(self, x):
        self.calls += 1
        return x * self.calls
    """,
    "[torch.rand(batch_size, dim)]",
)
#: Same counter; flips the cuDNN benchmark switch (tracked by the store) on its second call.
STATEFUL_FLIPPER = textwrap.dedent(
    """\
    import torch
    import torch.nn as nn


    class ModelNew(nn.Module):
        def __init__(self):
            super().__init__()
            self.register_buffer("calls", torch.zeros(()))

        def forward(self, x):
            self.calls += 1
            if int(self.calls) == 2:
                torch.backends.cudnn.benchmark = not torch.backends.cudnn.benchmark
            return x * self.calls
    """
)
RAISES_ON_D3 = _problem(
    """
    def forward(self, x):
        if float(x.abs().max()) < 0.02:
            raise ValueError("tiny inputs are not supported")
        return torch.relu(x)
    """,
    "[torch.rand(batch_size, dim)]",
)
RELU_CANDIDATE = textwrap.dedent(
    """\
    import torch
    import torch.nn as nn


    class ModelNew(nn.Module):
        def forward(self, x):
            return torch.clamp(x, min=0.0)
    """
)
OOM_PROBLEM = _problem(
    """
    def forward(self, x):
        raise RuntimeError("CUDA error: CUBLAS_STATUS_ALLOC_FAILED when calling cublasCreate")
    """,
    "[torch.rand(batch_size, dim)]",
)
WITH_INDEX = _problem(
    """
    def forward(self, x, idx):
        return x * 2 + idx.float().sum()
    """,
    "[torch.rand(batch_size, dim), torch.randint(0, 5, (batch_size,))]",
)
#: Correct on its first call; writes its integer input in place afterwards.
INDEX_WRITER = textwrap.dedent(
    """\
    import torch
    import torch.nn as nn


    class ModelNew(nn.Module):
        def forward(self, x, idx):
            out = x * 2 + idx.float().sum()
            idx.zero_()
            return out
    """
)


def _reference_item(problem_id: str, source: Path, gate: str, root: Path) -> list:
    item = {
        "gate": gate,
        "seed": 42,
        "problem_id": problem_id,
        "problem_source_path": str(source),
        "device": "cpu",
        "options": {refstore.OPTION: str(root)},
    }
    return refstore.reference_outcome(item)


def _rows(outcomes: list) -> list[dict]:
    return [
        o.to_row(
            "k",
            tf32_policy="torch-default",
            gpu_seconds=0.0,
            seed=42,
            run_id="r",
            attempt=1,
            code_sha256="0" * 64,
        )
        for o in outcomes
    ]


@pytest.fixture
def benchmark_switch():
    old = torch.backends.cudnn.benchmark
    yield
    torch.backends.cudnn.benchmark = old


def test_gate_c_switch_flip_with_a_stateful_reference_replays(
    tmp_path: Path, benchmark_switch: None
) -> None:
    problem_id = "L1/9101_StatefulCounter"
    source = tmp_path / "problem.py"
    source.write_text(STATEFUL)
    torch.backends.cudnn.benchmark = False
    inline = gate_c.run_gate_c(
        problem_id, STATEFUL_FLIPPER, problem_source=STATEFUL, device=CPU, families=("c1",)
    )
    torch.backends.cudnn.benchmark = False
    root = tmp_path / "store"
    (ref,) = _reference_item(problem_id, source, "ref_c", root)
    assert ref.verdict == "accept", ref.details
    refstore.USES.clear()
    stored = gate_c.run_gate_c(
        problem_id,
        STATEFUL_FLIPPER,
        problem_source=STATEFUL,
        device=CPU,
        families=("c1",),
        reference_store=str(root),
    )
    (lookup,) = refstore.USES
    assert lookup["used"] and lookup["inline_reason"] == "switches-changed"
    assert lookup["inline_from_draw"] == 2 and lookup["replayed_reference_forwards"] == 2
    assert not differences(_rows(inline), _rows(stored))


def test_a_raising_reference_makes_the_entry_unusable_not_an_error(tmp_path: Path) -> None:
    """Finding 4: a raised draw is never served; consumers compute inline."""
    problem_id = "L1/9102_RaisesOnTinyInputs"
    source = tmp_path / "problem.py"
    source.write_text(RAISES_ON_D3)
    root = tmp_path / "store"
    (ref,) = _reference_item(problem_id, source, "ref_c", root)
    assert ref.verdict == "error" and ref.details["reason"] == "entry-unusable"
    assert any("reference-raised" in p for p in ref.details["problems"])
    entry = Path(ref.details["entry_dir"])
    assert not list(entry.glob("draw-*.pt"))  # an unusable entry keeps no tensors
    inline = gate_c.run_gate_c(
        problem_id, RELU_CANDIDATE, problem_source=RAISES_ON_D3, device=CPU, families=("c1",)
    )
    refstore.USES.clear()
    stored = gate_c.run_gate_c(
        problem_id,
        RELU_CANDIDATE,
        problem_source=RAISES_ON_D3,
        device=CPU,
        families=("c1",),
        reference_store=str(root),
    )
    assert refstore.USES[-1]["reason"] == "entry-unusable"
    assert not differences(_rows(inline), _rows(stored))
    # inline, the raising configuration is inadmissible, never a verdict for every kernel
    d3 = [o for o in inline if o.config_id.startswith("c1/D3")]
    assert d3 and d3[0].details["reference_raised"]
    assert [o.verdict for o in inline if o.gate == "c1"][-1] == "accept"


def test_a_resource_failure_writes_no_entry_and_is_retried_as_contention(tmp_path: Path) -> None:
    problem_id = "L1/9103_AllocFails"
    source = tmp_path / "problem.py"
    source.write_text(OOM_PROBLEM)
    root = tmp_path / "store"
    for gate in ("ref_c", "ref_A5"):
        (ref,) = _reference_item(problem_id, source, gate, root)
        assert ref.verdict == "error" and ref.details["reason"] == "reference-resource-failure"
        assert not Path(ref.details["entry_dir"]).exists()
        assert contention_failure(_rows([ref])) == "oom-shared"


def test_a5_integer_input_written_between_checks(tmp_path: Path) -> None:
    from harness.q1.audit import run as audit

    problem_id = "L1/9104_WithIndex"
    source = tmp_path / "problem.py"
    source.write_text(WITH_INDEX)
    subject = audit.prepare(problem_id, WITH_INDEX, INDEX_WRITER, device=CPU)
    try:
        inline = audit.run_a5(subject)
    finally:
        subject.cleanup()
    root = tmp_path / "store"
    (ref,) = _reference_item(problem_id, source, "ref_A5", root)
    assert ref.verdict == "accept", ref.details
    subject = audit.prepare(problem_id, WITH_INDEX, INDEX_WRITER, device=CPU)
    refstore.USES.clear()
    try:
        stored = audit.run_a5(subject, reference_store=str(root))
    finally:
        subject.cleanup()
    (lookup,) = refstore.USES
    assert lookup["used"] and lookup["inline_reason"] == "inputs-differ"
    assert lookup["inline_from_tag"] == "EXC-01/pos_inf"
    assert not differences(_rows(inline), _rows(stored))


def test_a5_na_keeps_the_reference_exception_text() -> None:
    from harness.q1.audit import lethe_contracts

    class Ref(torch.nn.Module):
        def forward(self, x):
            if torch.isnan(x).any():
                raise RuntimeError("CUDA out of memory. Tried to allocate 3.24 GiB")
            return x

    x = [torch.rand(4, 8)]
    results = lethe_contracts.run_a5(Ref(), Ref(), x, device=CPU)
    exc01 = next(r for r in results if r["check"] == "EXC-01")
    assert any("CUDA out of memory" in reason for reason in exc01["na_reasons"])
    assert contention_failure([{"verdict": "error", "details": {"checks": results}}]) == (
        "oom-shared"
    )


def test_fingerprint() -> None:
    x = torch.rand(3, 70_001)
    idx = torch.randint(0, 5, (7,))
    base = refstore.fingerprint([x, idx, 3])
    assert base == refstore.fingerprint([x.clone(), idx.clone(), 3])
    y = x.clone()
    y[2, 70_000] += 1e-6
    assert refstore.fingerprint([y, idx, 3]) != base
    z = idx.clone()
    z[0] += 1
    assert refstore.fingerprint([x, z, 3]) != base
    assert refstore.fingerprint([x, idx, 4]) != base
    assert refstore.fingerprint([x.double(), idx, 3]) != base
    assert refstore.fingerprint([x.t()]) == refstore.fingerprint([x.t().contiguous()])
    assert refstore.fingerprint([torch.zeros(0), torch.tensor(True)])
    # views at offsets an integer view cannot start at (half and byte tensors)
    half = torch.rand(9, dtype=torch.float16)
    assert refstore.fingerprint([half[1:]]) == refstore.fingerprint([half[1:].clone()])
    raw = torch.arange(11, dtype=torch.uint8)
    assert refstore.fingerprint([raw[3:]]) == refstore.fingerprint([raw[3:].clone()])
    assert refstore.safe_fingerprint([object()]) is not None  # repr of other values

    class Broken(torch.Tensor):
        def reshape(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
            raise RuntimeError("cannot reshape")

    assert refstore.safe_fingerprint([torch.zeros(3).as_subclass(Broken)]) is None


def test_disk_cap_and_deleting_draws(tmp_path: Path) -> None:
    def built() -> refstore.Built:
        return refstore.Built(
            draws=[refstore.Draw({"kind": "ok"}, torch.zeros(1000))],
            facts=refstore.environment_facts(),
        )

    def payload(seed: int) -> dict:
        return refstore.key_payload(
            "A1",
            problem_id="L1/9105_Cap",
            problem_source="x",
            seed=seed,
            device_type="cpu",
            params={},
        )

    first = refstore.write_entry(tmp_path, payload(1), built(), cap_bytes=6000)
    assert first["usable"] and refstore.live_bytes(tmp_path) > 4000
    second = refstore.write_entry(tmp_path, payload(2), built(), cap_bytes=6000)
    assert not second["usable"] and second["problems"][0].startswith("store-cap")
    path = refstore.entry_dir(tmp_path, "A1", refstore.key_of(payload(2)))
    assert not list(path.glob("draw-*.pt"))
    first_path = refstore.entry_dir(tmp_path, "A1", refstore.key_of(payload(1)))
    assert refstore.delete_draws(first_path) > 4000
    assert refstore.live_bytes(tmp_path) == 0
    assert refstore.lookup(tmp_path, payload(1), draws=1) is None  # incomplete now
    assert json.loads((first_path / "entry.json").read_text())["usable"]
