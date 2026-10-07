"""Gates (a), (b), (c) on CPU tensors with the synthetic fixtures (Triton interpreter).

Needs torch and triton (the research image); skipped elsewhere, and skipped
when a GPU is visible because the fixtures are CPU-only by policy.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("TRITON_INTERPRET", "1")
torch = pytest.importorskip("torch")
pytest.importorskip("triton")
if torch.cuda.is_available():  # pragma: no cover - CPU-only fixtures
    pytest.skip("fixtures are CPU-only", allow_module_level=True)
if os.environ.get("TRITON_INTERPRET") != "1":  # pragma: no cover
    pytest.skip("needs TRITON_INTERPRET=1", allow_module_level=True)

from harness.q1 import doctor_fixtures as fx  # noqa: E402
from harness.q1 import problems as problem_lib  # noqa: E402
from harness.q1 import shapes  # noqa: E402
from harness.q1.gates import gate_a, gate_b, gate_c  # noqa: E402
from harness.q1.gates.common import kernelbench_trial_seeds  # noqa: E402

KERNELGYM = Path(os.environ.get("KERNELGYM_SRC", "/upstream/KernelGYM"))


def _problem(name: str) -> str:
    return fx.PROBLEMS[str(fx.KERNELS[name]["problem"])]


def _kernel(name: str) -> str:
    return str(fx.KERNELS[name]["source"])


def _manifest(problem_id: str) -> dict:
    source = fx.PROBLEMS[problem_id]
    analysis = problem_lib.analyze_problem(problem_id, source)

    def input_bytes(overrides: dict[str, int]) -> int:
        variant = problem_lib.override_constants(source, analysis, overrides)
        return int(problem_lib.meta_input_summary(variant)["input_bytes"])

    entry = shapes.build_problem_manifest(
        analysis, problem_sha256="0" * 64, input_bytes=input_bytes
    )
    return {"problems": {problem_id: entry}}


def test_trial_seeds_follow_kernelbench() -> None:
    torch.manual_seed(42)
    expected = [int(torch.randint(0, 2**32 - 1, (1,)).item()) for _ in range(5)]
    assert kernelbench_trial_seeds(42, 5) == expected


@pytest.mark.parametrize(
    ("kernel", "variant", "verdict"),
    [
        ("relu_correct", "a", "accept"),
        ("relu_correct", "a_head_1e-4", "accept"),
        ("rowsum_tail_drop", "a", "accept"),
        ("rowsum_tail_drop", "a_1e-3", "reject"),
        ("rowsum_tail_drop", "a_head_1e-4", "reject"),
        ("relu_cached", "a", "reject"),
        ("ce_torch_control", "a", "accept"),
        ("ce_torch_control", "a_head_1e-4", "error"),
        ("relu_identity_control", "a_static", "reject"),
    ],
)
def test_gate_a_variants(kernel: str, variant: str, verdict: str) -> None:
    outcome = gate_a.run_gate_a(_problem(kernel), _kernel(kernel), variant=variant, device="cpu")
    assert outcome.verdict == verdict, outcome.details
    if verdict == "error":
        assert outcome.details["reason"] == "reference-raised"
        assert outcome.details["upstream_equivalent"] == "reject"


@pytest.mark.parametrize(
    "kernel", ["relu_correct", "relu_removed", "relu_cached", "rowsum_tail_drop", "argmax_control"]
)
def test_gate_a_transcription_matches_vendored_upstream(kernel: str) -> None:
    ours = gate_a.run_gate_a(_problem(kernel), _kernel(kernel), device="cpu").verdict
    upstream = gate_a.upstream_run_and_check_correctness_cpu(_problem(kernel), _kernel(kernel))
    assert (ours == "accept") == upstream


def test_b1_launch_detection() -> None:
    assert (
        gate_b.run_gate_b1(_problem("relu_correct"), _kernel("relu_correct"), device="cpu").verdict
        == "accept"
    )
    identity = gate_b.run_gate_b1(
        _problem("relu_identity_control"), _kernel("relu_identity_control"), device="cpu"
    )
    assert identity.verdict == "reject"
    assert identity.details["per_mode"] == {"inference_mode": False, "enable_grad": False}
    # Released-behaviour blind spot: a trivial launch satisfies b1.
    assert (
        gate_b.run_gate_b1(
            _problem("relu_decoy_launch"), _kernel("relu_decoy_launch"), device="cpu"
        ).verdict
        == "accept"
    )


def test_b1_replays_the_released_call_history() -> None:
    """Review finding: released b1 hooks the module's 7th and 9th calls (after b0's five
    trials); a fresh module's 2nd and 4th calls let a call-count switch pass."""
    problem, kernel = _problem("relu_call_count_switch"), _kernel("relu_call_count_switch")
    outcome = gate_b.run_gate_b1(problem, kernel, device="cpu")
    assert outcome.verdict == "reject", outcome.details
    assert outcome.details["per_mode"] == {"inference_mode": False, "enable_grad": False}
    assert outcome.details["b0_calls_replayed"] == gate_b.B0_TRIALS
    from harness.q1.gates.common import load_candidate, load_reference, set_seed

    _, get_init, get_inputs = load_reference(problem)
    loaded = load_candidate(kernel)
    try:
        set_seed(42)
        fresh = loaded.model_class(*get_init())
        used, _, _ = gate_b.detect_launches(fresh, get_inputs(), device=torch.device("cpu"))
    finally:
        loaded.cleanup()
    assert used  # the same detection on a module with no history is fooled


def test_b2_retries_an_empty_profile_once() -> None:
    class Counting(torch.nn.Module):
        calls = 0

        def forward(self, x):
            Counting.calls += 1
            return x + 1

    x = torch.ones(4)
    for retries, expected in ((0, 3 + 10 + 10), (1, 3 + 10 + 10 + 10)):
        Counting.calls = 0
        rows = gate_b.profiler_rows(Counting(), [x], device=torch.device("cpu"), retries=retries)
        assert rows == [] and Counting.calls == expected  # CPU rows carry no device time


def test_launch_hook_restores_triton_classes() -> None:
    from triton.runtime.jit import JITFunction, KernelInterface

    before = (
        JITFunction.__dict__.get("__getitem__"),
        KernelInterface.__dict__["__getitem__"],
        JITFunction.__dict__["run"],
    )
    with gate_b.LaunchHook():
        assert JITFunction.__dict__["run"] is not before[2]
    after = (
        JITFunction.__dict__.get("__getitem__"),
        KernelInterface.__dict__["__getitem__"],
        JITFunction.__dict__["run"],
    )
    assert before == after


def test_b2_coverage_rule() -> None:
    rows = [{"name": "relu_kernel_0d1d"}, {"name": "aten::sum"}]
    assert gate_b.coverage(["relu_kernel grid=(4,)"], rows)["decoy"] is False
    assert gate_b.coverage(["relu_kernel grid=(4,)"], [{"name": "aten::relu"}])["decoy"] is True
    assert gate_b.coverage(["relu_kernel grid=(4,)"], [])["decoy"] is False


@pytest.mark.skipif(not (KERNELGYM / "kernelgym").is_dir(), reason="no KernelGYM clone")
def test_b1_and_b2_agree_with_unmodified_kernelgym() -> None:
    import sys
    import types

    from harness.q1.gates import b_native
    from harness.q1.gates.common import load_candidate, load_reference, set_seed

    clone = b_native.resolve_clone(KERNELGYM)
    upstream_detect = b_native.load_triton_detect_standalone(clone)
    for name in ("relu_correct", "relu_identity_control", "relu_decoy_launch"):
        _, get_init, get_inputs = load_reference(_problem(name))
        loaded = load_candidate(_kernel(name))
        try:
            set_seed(42)
            model = loaded.model_class(*get_init())
            set_seed(42)
            inputs = get_inputs()
            ours, _, _ = gate_b.detect_launches(model, inputs, device=torch.device("cpu"))
            theirs = upstream_detect.detect_triton_usage_for_module(
                model, *inputs, warmup=1, steps=1, use_cuda=False
            )
        finally:
            loaded.cleanup()
        assert ours == bool(theirs), name
    # Coverage rule: load the unmodified profiling module with a settings stub
    # (its only dependency outside torch is kernelgym.config.settings).
    stub = types.ModuleType("kernelgym.config")
    stub.settings = types.SimpleNamespace(profiling_activities=["cpu"])
    sys.modules.setdefault("kernelgym.config", stub)
    profiling = b_native.load_upstream_module(clone, "profiling")
    cases = [
        (["relu_kernel grid=(4,)"], [{"name": "relu_kernel_0d1d"}, {"name": "aten::sum"}]),
        (["relu_kernel grid=(4,)"], [{"name": "aten::relu"}]),
        (["Add grid=None"], [{"name": "aten::add"}]),
    ]
    for captures, rows in cases:
        table = {"kernels": [{**r, "cuda_time_us": 1.0, "cpu_time_us": 1.0} for r in rows]}
        theirs = profiling.compute_triton_kernel_coverage(captures, table)
        ours = gate_b.coverage(captures, rows)
        assert ours["num_custom_kernels"] == theirs["num_custom_kernels"]
        assert ours["num_total_kernels"] == theirs["num_total_kernels"]


@pytest.mark.skipif(not (KERNELGYM / "kernelgym").is_dir(), reason="no KernelGYM clone")
def test_capture_names_match_kernelgym() -> None:
    """Black-box parity of capture records with the unmodified clone (gate_b.py was
    rewritten from the spec without reading KernelGYM's source)."""
    from triton.runtime.autotuner import Autotuner
    from triton.runtime.jit import JITFunction, KernelInterface

    from harness.q1.gates import b_native

    upstream = b_native.load_triton_detect_standalone(b_native.resolve_clone(KERNELGYM))

    def raw(name):
        def f():
            return None

        f.__name__ = name
        return f

    class Named:
        def __init__(self, **attrs):
            for key, value in attrs.items():
                setattr(self, key, value)

    def make(base, **attrs):
        class Probe(base):
            def __init__(self):
                pass

        obj = Probe()
        for key, value in attrs.items():
            object.__setattr__(obj, key, value)
        return obj

    class Call(torch.nn.Module):
        def __init__(self, obj, path):
            super().__init__()
            self.obj, self.path = obj, path

        def forward(self, x):
            try:
                if self.path == "getitem":
                    self.obj[(3,)](x)
                else:
                    getattr(self.obj, self.path)(x, grid=(5,))
            except Exception:
                pass
            return x

    cases = [
        (KernelInterface, "getitem", {"fn": raw("fa")}),
        (KernelInterface, "getitem", {"fn": Named(kernel_name="fk")}),
        (KernelInterface, "getitem", {"kernel": Named(fn=raw("fc"))}),
        (KernelInterface, "getitem", {"kernel": Named(kernel=Named(kernel=Named(fn=raw("x"))))}),
        (KernelInterface, "getitem", {"kernel": Named(name="unknown"), "name": "top"}),
        (KernelInterface, "getitem", {"fn": None, "name": "nm"}),
        (KernelInterface, "getitem", {"name": 5, "kernel_name": "kn"}),
        (KernelInterface, "run", {"fn": raw("q")}),
        (KernelInterface, "__call__", {"fn": raw("q")}),
        (JITFunction, "getitem", {"fn": raw("jf")}),
        (JITFunction, "getitem", {"fn": Named(), "kernel": Named(name="kk")}),
        (JITFunction, "run", {"fn": Named(name="fobj")}),
        (JITFunction, "__call__", {"fn": raw("jcall")}),
        (Autotuner, "getitem", {"fn": raw("atk")}),
        (Autotuner, "run", {"fn": Named(kernel_name="atn")}),
    ]
    x = torch.zeros(4)
    for base, path, attrs in cases:
        _, theirs = upstream.detect_triton_usage_for_module(
            Call(make(base, **attrs), path),
            x,
            warmup=0,
            steps=1,
            use_cuda=False,
            return_matches=True,
        )
        _, ours, _ = gate_b.detect_launches(
            Call(make(base, **attrs), path), [x], warmup=0, device=torch.device("cpu")
        )
        assert sorted(set(theirs or [])) == ours, (base.__name__, path, attrs)


def test_gate_c_ladder_on_fixtures() -> None:
    manifest = _manifest("L1/9001_SyntheticReLU")

    def aggregates(kernel: str) -> dict[str, str]:
        rows = gate_c.run_gate_c(
            "L1/9001_SyntheticReLU",
            _kernel(kernel),
            problem_source=_problem(kernel),
            device="cpu",
            manifest=manifest,
        )
        return {r.gate: r.verdict for r in rows if r.config_id == "aggregate"}

    correct = aggregates("relu_correct")
    assert correct == {
        "c1": "accept",
        "c2": "accept",
        "c3": "accept",
        "c_1e-2": "accept",
        "c_kbv_raw": "accept",
    }
    assert aggregates("relu_removed")["c1"] == "reject"
    refusing = aggregates("relu_refuses_shapes")
    assert refusing["c1"] == "accept" and refusing["c2"] == "reject"


def test_gate_c_seeds_and_kbv_table() -> None:
    specs = gate_c.c_configs("L1/90_cumprod", families=("c1",))
    assert [s.draw for s in specs] == ["D1", "D3", "D4"]
    assert [s.seed for s in specs] == [1042, 1043, 1044]
    replicate = gate_c.c_configs("L1/90_cumprod", families=("c1",), replicate_seed=43)
    assert [s.seed for s in replicate] == [1142, 1143, 1144]
    hinge = gate_c.c_configs("L1/100_HingeLoss", families=("c1",))
    assert hinge[-1].draw == "D5-alternating-targets"
    targets = gate_c.transform_inputs([torch.rand(6, 3), torch.ones(6)], "D5-alternating-targets")
    assert targets[1].tolist() == [-1.0, 1.0, -1.0, 1.0, -1.0, 1.0]
    shaped = gate_c.c_configs("L1/19_ReLU", families=("c2",))
    assert [s.draw for s in shaped[:2]] == ["D1", "D4"] and shaped[0].seed == 2042


def test_gate_c_kbv_compat_casts_integer_targets() -> None:
    source = _problem("ce_torch_control")
    rows = gate_c.run_gate_c(
        "L1/9003_SyntheticCrossEntropy",
        _kernel("ce_torch_control"),
        problem_source=source,
        device="cpu",
        families=("c1",),
        validity="off",
        kbv_compat=True,
        manifest={"problems": {}},
    )
    per_config = [r for r in rows if r.config_id != "aggregate"]
    assert all(r.details.get("reference_raised") for r in per_config)
    verdicts = {r.gate: r.verdict for r in rows if r.config_id == "aggregate"}
    assert verdicts["c_kbv_raw"] == "accept"  # KBV skips configs whose reference raises
    assert verdicts["c1"] == "error"  # Q1: unrefereeable, not a pass


def test_validity_gate_rejects_unstable_references() -> None:
    model = torch.nn.Identity()
    ok = gate_c.validity_check(
        model, [torch.rand(4)], torch.rand(4) * 0 + 1, device=torch.device("cpu"), tolerance=1e-3
    )
    assert ok["admissible"] is False  # output differs from the fp64 replay
    nan = gate_c.validity_check(
        model,
        [torch.tensor([float("nan")])],
        torch.tensor([float("nan")]),
        device=torch.device("cpu"),
        tolerance=1e-3,
    )
    assert "reference-nonfinite" in nan["reasons"]
    x = torch.rand(8)
    good = gate_c.validity_check(model, [x], x.clone(), device=torch.device("cpu"), tolerance=1e-3)
    assert good["admissible"] is True
