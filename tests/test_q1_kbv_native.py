"""KBV-native fidelity runner against gate (c1) in KBV-compatibility mode (CPU).

Needs torch, Triton (interpreter) and an unmodified kernel_bench_verified clone
at the pinned revision in ``KBV_SRC`` (outside the repository; never vendored).
A synthetic problem is written into a scratch copy of the clone's layout in
KBV's own hidden-test format, so the differential runs on small CPU tensors;
upstream ``src/eval.py`` is copied byte for byte from the clone.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

os.environ.setdefault("TRITON_INTERPRET", "1")
torch = pytest.importorskip("torch")
pytest.importorskip("triton")
if torch.cuda.is_available():  # pragma: no cover - CPU-only fixtures
    pytest.skip("fixtures are CPU-only", allow_module_level=True)
KBV_SRC = os.environ.get("KBV_SRC")
if not KBV_SRC:
    pytest.skip("KBV_SRC (unmodified kernel_bench_verified clone) not set", allow_module_level=True)

from harness.q1 import doctor_fixtures as fx  # noqa: E402
from harness.q1.gates import kbv_native  # noqa: E402
from harness.q1.gates.gate_c import run_gate_c  # noqa: E402
from harness.q1.schema import KBV_REVISION  # noqa: E402

PROBLEM = "L1/9001_SyntheticReLU"
HIDDEN = """import torch
import importlib.util
import os

_PROB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
    '../../KernelBench/level1/9001_SyntheticReLU.py'))


def _get_inputs():
    _spec = importlib.util.spec_from_file_location('_prob', _PROB_PATH)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod.get_inputs()


def _scale(inputs, factor):
    return [t * factor if isinstance(t, torch.Tensor) and t.is_floating_point() else t
            for t in inputs]


def get_hidden_inputs():
    configs = []
    configs.append(_get_inputs())
    configs.append(_scale(_get_inputs(), 3.0))
    configs.append(_scale(_get_inputs(), 0.01))
    configs.append(_scale(_get_inputs(), -1.0))
    return configs
"""


@pytest.fixture(scope="module")
def fake_clone(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("kbv") / "kernel_bench_verified"
    (root / "src").mkdir(parents=True)
    shutil.copyfile(Path(KBV_SRC) / "src" / "eval.py", root / "src" / "eval.py")
    level = root / "KernelBench" / "level1"
    level.mkdir(parents=True)
    # KBV prepends a 6-line Meta header; the runner strips the first 6 lines only
    # when they start with KBV's copyright line, so this copy is compared as is.
    (level / "9001_SyntheticReLU.py").write_text(fx.PROBLEMS[PROBLEM])
    hidden = root / "hidden_tests" / "level1"
    hidden.mkdir(parents=True)
    (hidden / "9001_hidden.py").write_text(HIDDEN)
    (root / "REVISION").write_text(KBV_REVISION + "\n")
    return root


@pytest.fixture(autouse=True)
def cpu_synchronize(monkeypatch: pytest.MonkeyPatch) -> None:
    # Upstream calls torch.cuda.synchronize(device=...); on a CPU-only process it is
    # a no-op for the duration of the test (the gate (a) CPU differential does the same).
    monkeypatch.setattr(torch.cuda, "synchronize", lambda *a, **k: None)


@pytest.mark.parametrize(
    ("kernel", "expected"),
    [
        ("relu_correct", ["accept"] * 4),
        ("relu_removed", ["accept", "accept", "accept", "reject"]),
    ],
)
def test_native_matches_kbv_compat_per_config(
    fake_clone: Path, kernel: str, expected: list[str]
) -> None:
    source = str(fx.KERNELS[kernel]["source"])
    problem = fx.PROBLEMS[PROBLEM]
    native = kbv_native.run_kbv_native(
        PROBLEM, source, clone=fake_clone, seed=42, device="cpu", ours_problem_source=problem
    )
    ours = run_gate_c(
        PROBLEM,
        source,
        problem_source=problem,
        families=("c1",),
        replicate_seed=42,
        device="cpu",
        validity="off",
        kbv_compat=True,
    )
    native_configs = [o.verdict for o in native if o.config_id != "aggregate"]
    ours_configs = [o.verdict for o in ours if o.gate == "c1" and o.config_id != "aggregate"]
    assert native_configs == ours_configs == expected
    aggregate = next(o for o in native if o.config_id == "aggregate")
    assert aggregate.verdict == ("accept" if all(v == "accept" for v in expected) else "reject")
    assert aggregate.details["adaptations"] == ["stub-utils", "file-backed-candidate-loader"]
    assert aggregate.details["kbv_problem_equals_ours_after_header"] is True


def test_clone_checks(tmp_path: Path, fake_clone: Path) -> None:
    with pytest.raises(kbv_native.NativeKbvError):
        kbv_native.resolve_clone(tmp_path / "missing")
    wrong = tmp_path / "wrong"
    shutil.copytree(fake_clone, wrong)
    (wrong / "REVISION").write_text("0" * 40 + "\n")
    with pytest.raises(kbv_native.NativeKbvError, match="expected"):
        kbv_native.resolve_clone(wrong)
