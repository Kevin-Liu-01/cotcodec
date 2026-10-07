"""Independent audit A1-A5, tiers and calibration on CPU tensors.

Needs torch (and triton for the Triton fixtures); skipped elsewhere and when a
GPU is visible.
"""

from __future__ import annotations

import math
import os

import pytest

os.environ.setdefault("TRITON_INTERPRET", "1")
torch = pytest.importorskip("torch")
pytest.importorskip("triton")
if torch.cuda.is_available():  # pragma: no cover - CPU-only fixtures
    pytest.skip("fixtures are CPU-only", allow_module_level=True)

from harness.q1 import doctor_fixtures as fx  # noqa: E402
from harness.q1.audit import contracts, lethe_contracts, oracle, tiers, values  # noqa: E402
from harness.q1.audit import run as audit  # noqa: E402


def _subject(name: str) -> audit.AuditSubject:
    spec = fx.KERNELS[name]
    problem_id = str(spec["problem"])
    return audit.prepare(problem_id, fx.PROBLEMS[problem_id], str(spec["source"]), device="cpu")


def _reference(r64, r32, cpu=None, tf32=None, ops=()) -> oracle.OracleReference:
    def err(x):
        return (
            None
            if x is None
            else max(oracle.scaled_error(a, b) for a, b in zip(x, r64, strict=True))
        )

    return oracle.OracleReference(
        r64=r64,
        r32_device=r32,
        r32_cpu=cpu,
        r32_tf32=tf32,
        e_device=err(r32),
        e_cpu=err(cpu),
        e_tf32=err(tf32),
        ops=list(ops),
    )


def test_scaled_error_and_masks() -> None:
    r = torch.tensor([1.0, -2.0, 0.0], dtype=torch.float64)
    assert oracle.scaled_error(r.float(), r) == 0.0
    x = torch.tensor([1.001, -2.0, 0.0])
    assert math.isclose(oracle.scaled_error(x, r), 0.001 / (1 + 2e-3), rel_tol=1e-3)
    assert oracle.scaled_error(torch.zeros(2), r) == math.inf
    nan = torch.tensor([float("nan"), 1.0])
    assert oracle.masks_equal(nan, nan.double())
    assert not oracle.masks_equal(torch.tensor([0.0, 1.0]), nan.double())
    assert oracle.threshold([0.0, 0.0], 16) == oracle.T_FLOOR


def test_tf32_policy_widens_threshold_only_for_matmul_or_tl_dot() -> None:
    r64 = [torch.tensor([1.0, 2.0], dtype=torch.float64)]
    strict = [torch.tensor([1.0, 2.0])]
    tf32 = [torch.tensor([1.001, 2.0])]
    plain = _reference(r64, strict, cpu=strict, tf32=tf32, ops=["relu"])
    gemm = _reference(r64, strict, cpu=strict, tf32=tf32, ops=["mm"])
    t_plain, applied_plain = oracle.a1_threshold(
        plain, policy="tf32-admissible", multiplier=16, candidate_tl_dot=False
    )
    t_gemm, applied_gemm = oracle.a1_threshold(
        gemm, policy="tf32-admissible", multiplier=16, candidate_tl_dot=False
    )
    t_dot, applied_dot = oracle.a1_threshold(
        plain, policy="tf32-admissible", multiplier=16, candidate_tl_dot=True
    )
    t_strict, _ = oracle.a1_threshold(
        gemm, policy="strict-fp32", multiplier=16, candidate_tl_dot=True
    )
    assert not applied_plain and t_plain == oracle.T_FLOOR
    assert applied_gemm and applied_dot and t_gemm > 0.01 and t_dot == t_gemm
    assert t_strict == oracle.T_FLOOR
    candidate = torch.tensor([1.0005, 2.0])
    assert oracle.a1_compare(candidate, gemm, policy="tf32-admissible").passed
    assert not oracle.a1_compare(candidate, gemm, policy="strict-fp32").passed
    assert oracle.candidate_uses_tl_dot("acc += tl.dot(a, b)")
    assert not oracle.candidate_uses_tl_dot("tl.sum(a)")


def test_integer_outputs_need_exact_match_except_certified_near_ties() -> None:
    r64 = [torch.tensor([0, 1, 2])]
    r32 = [torch.tensor([0, 1, 3])]  # fp32 itself flips position 2: a near-tie
    ref = _reference(r64, r32, cpu=r32)
    ok = oracle.a1_compare(torch.tensor([0, 1, 3]), ref, policy="strict-fp32")
    assert ok.passed and ok.certified_near_ties == 1
    bad = oracle.a1_compare(torch.tensor([1, 1, 2]), ref, policy="strict-fp32")
    assert not bad.passed and bad.reason == "integer-mismatch"


def test_calibration_raises_once_to_a_power_of_two() -> None:
    assert oracle.calibrate_multiplier([1.0, 15.0]) == (16, False)
    assert oracle.calibrate_multiplier([17.0]) == (32, True)
    assert oracle.calibrate_multiplier([100.0]) == (128, True)
    with pytest.raises(ValueError):
        oracle.calibrate_multiplier([math.inf])


def test_tiers() -> None:
    assert tiers.tier_verdicts(
        {"A1": "accept", "A2": "accept", "A3": "refuse", "A4": "accept"}
    ) == {"N": "accept", "G": "accept", "G-strict": "reject", "c-disjoint": "accept"}
    assert (
        tiers.tier_verdicts({"A1": "accept", "A2": "reject", "A3": "accept", "A4": "accept"})["N"]
        == "reject"
    )
    assert (
        tiers.tier_verdicts({"A1": "error", "A2": "accept", "A3": "accept", "A4": "accept"})["G"]
        == "error"
    )
    details = {"counts": {"crash-after-launch": 0}, "silent_wrong_all_within_64T": True}
    channels = {"A1": "reject", "A2": "accept", "A3": "accept", "A4": "accept"}
    assert tiers.precision_only(details, channels)
    assert not tiers.precision_only(details, {**channels, "A2": "reject"})


def test_audit_version_hash_tracks_constants() -> None:
    a = tiers.audit_version_hash(multiplier=16, multiplier_raised=False)
    b = tiers.audit_version_hash(multiplier=32, multiplier_raised=True)
    assert a["audit_version_sha256"] != b["audit_version_sha256"]
    assert set(a["files"]) == set(tiers.AUDIT_FILES)


def test_value_distributions() -> None:
    template = [torch.rand(4, 9), torch.randint(0, 3, (4,))]
    torch.manual_seed(0)
    drawn = {name: values.apply_distribution(template, name) for name in values.DISTRIBUTIONS}
    assert all(torch.equal(d[1], template[1]) for d in drawn.values())
    assert bool((drawn["allneg"][0] < 0).all())
    assert bool((drawn["samesign100"][0] >= 0).all())
    assert torch.equal(drawn["ties"][0] * 8, torch.round(drawn["ties"][0] * 8))
    rows = drawn["constrows"][0]
    assert torch.equal(rows, rows[:, :1].expand_as(rows))
    torch.manual_seed(1)
    spiky = values.apply_distribution(template, "spiky")[0]
    torch.manual_seed(1)
    ratio = spiky / torch.rand(4, 9)
    for index in ((3, 0), (0, 8), (3, 8)):  # last element along each axis, and the flat last
        assert ratio[index] >= 999.0


def test_a1_a2_a3_on_fixtures() -> None:
    correct = _subject("relu_correct")
    removed = _subject("relu_removed")
    try:
        a1 = [r for r in audit.run_a1(correct) if r.config_id == "aggregate"]
        assert {r.details["policy"] for r in a1} == set(oracle.POLICIES)
        assert {r.verdict for r in a1} == {"accept"}
        assert {r.verdict for r in audit.run_a1(removed) if r.config_id == "aggregate"} == {
            "accept"
        }  # rand inputs are non-negative: ReLU removal is invisible at native draws
        a2_removed = [r for r in audit.run_a2(removed) if r.config_id == "aggregate"]
        assert {r.verdict for r in a2_removed} == {"reject"}
    finally:
        correct.cleanup()
        removed.cleanup()


def test_a3_classifies_refusals_and_silent_failures() -> None:
    from harness.q1 import problems as problem_lib
    from harness.q1 import shapes

    problem_id = "L1/9001_SyntheticReLU"
    source = fx.PROBLEMS[problem_id]
    analysis = problem_lib.analyze_problem(problem_id, source)

    def input_bytes(overrides: dict[str, int]) -> int:
        variant = problem_lib.override_constants(source, analysis, overrides)
        return int(problem_lib.meta_input_summary(variant)["input_bytes"])

    entry = shapes.build_problem_manifest(
        analysis, problem_sha256="0" * 64, input_bytes=input_bytes
    )
    outcomes = {}
    for name in ("relu_refuses_shapes", "relu_native_only"):
        subject = _subject(name)
        try:
            rows = audit.run_a3(subject, manifest_entry=entry)
        finally:
            subject.cleanup()
        outcomes[name] = next(r for r in rows if r.config_id == "aggregate")
    assert outcomes["relu_refuses_shapes"].verdict == "refuse"
    assert outcomes["relu_refuses_shapes"].details["counts"]["refusal-before-launch"] >= 1
    assert outcomes["relu_native_only"].verdict == "reject"
    assert outcomes["relu_native_only"].details["counts"]["silent-wrong"] >= 1


@pytest.mark.parametrize(
    ("name", "failed"),
    [
        ("relu_correct", set()),
        ("relu_inplace", {"no_input_aliasing", "inputs_unmodified"}),
        ("relu_cached", {"no_output_reuse"}),
        ("relu_nondeterministic", {"determinism"}),
        ("relu_empty_tail", {"dual_poison_factory"}),
    ],
)
def test_a4_contracts(name: str, failed: set[str]) -> None:
    subject = _subject(name)
    try:
        (row,) = audit.run_a4(subject)
    finally:
        subject.cleanup()
    assert failed <= set(row.details["failed"])
    if not failed:
        assert row.verdict == "accept"
    else:
        assert row.verdict == "reject"


class _ModeSensitive(torch.nn.Module):
    """Output depends on training mode, as BatchNorm and Dropout do."""

    def forward(self, x):
        return x * (2.0 if self.training else 1.0)


class _ModeSensitiveWrong(torch.nn.Module):
    def forward(self, x):
        return x * (1.0 if self.training else 2.0)


def test_a5_lethe_style_checks_keep_training_mode() -> None:
    reference, candidate = _ModeSensitive(), _ModeSensitive()
    results = lethe_contracts.run_a5(
        reference, candidate, [torch.randn(8, 4)], device=torch.device("cpu")
    )
    assert {r["check"]: r["status"] for r in results} == dict.fromkeys(
        lethe_contracts.CHECKS, "pass"
    )
    assert reference.training and candidate.training
    wrong = lethe_contracts.run_a5(
        _ModeSensitive(), _ModeSensitiveWrong(), [torch.randn(8, 4)], device=torch.device("cpu")
    )
    assert {r["check"]: r["status"] for r in wrong}["PRC-01"] == "fail"


def test_sanitizer_wrapping() -> None:
    cmd = contracts.sanitizer_command(["python", "-m", "harness.q1.worker", "i.json", "o.jsonl"])
    assert cmd[:3] == ["compute-sanitizer", "--tool", "memcheck"]
    assert contracts.interpret_sanitizer(0).passed is True
    assert contracts.interpret_sanitizer(contracts.SANITIZER_EXIT_CODE).passed is False
    assert contracts.interpret_sanitizer(1).passed is None


def test_tiers_drop_vacuous_channels_only_for_a2_and_a3() -> None:
    channels = {"A1": "accept", "A2": "error", "A3": "error", "A4": "accept"}
    assert tiers.tier_verdicts(channels)["G"] == "error"
    assert tiers.tier_verdicts(channels, vacuous=("A2", "A3")) == {
        "N": "accept",
        "G": "accept",
        "G-strict": "accept",
        "c-disjoint": "accept",
    }
    rejecting = {**channels, "A1": "reject"}
    assert tiers.tier_verdicts(rejecting, vacuous=("A2", "A3"))["G"] == "reject"
    with pytest.raises(ValueError):
        tiers.tier_verdicts(channels, vacuous=("A1",))


def test_required_multiplier_is_defined_for_exact_references() -> None:
    """Review finding: e / max(e_r32) was undefined when the fp32 reference is exact."""
    from harness.q1.audit.calibration import FAULT_CEILING, required_multiplier

    assert required_multiplier(0.0, [0.0, 0.0]) == 0.0  # exact candidate, exact reference
    assert required_multiplier(oracle.T_FLOOR / 2, [0.0]) == 0.0  # inside the floor
    assert math.isinf(required_multiplier(1e-3, [0.0, 0.0]))  # no M can pass it
    assert required_multiplier(8e-6, [1e-7, 4e-7]) == pytest.approx(20.0)
    assert required_multiplier(1.0, [None, math.inf]) == 0.0  # T is infinite
    assert math.isinf(required_multiplier(None, [1e-7]))
    assert FAULT_CEILING == 1024.0


def _a1_rows(kernel: str, draws: list[dict]) -> list[dict]:
    from harness.q1.schema import make_verdict_row

    rows = []
    for index, extra in enumerate(draws):
        details = {
            "admissible": True,
            "candidate_raised": False,
            "e_r32_device": 1e-7,
            "e_r32_cpu": 1e-7,
            "e_r32_tf32": None,
            "tf32-admissible": {"e": 1e-7, "tf32_applied": False, "reason": ""},
            **extra,
        }
        rows.append(
            make_verdict_row(
                kernel_id=kernel,
                gate="A1",
                config_id=f"A1/native/seed-{6042 + index}",
                verdict="accept",
                tf32_policy="tf32-admissible",
                gpu_seconds=0.0,
                details=details,
                seed=42,
            )
        )
    return rows


def test_calibration_driver_classifies_and_raises_m_once() -> None:
    from harness.q1.audit.calibration import calibrate

    table = {
        name: {"kind": "substrate", "source_kind": "inductor", "problem_id": f"L1/{i}_P"}
        for i, name in enumerate(("ok", "precision", "exact", "fault", "raised", "unref"))
    }
    table["s2"] = {"kind": "substrate", "source_kind": "liger", "problem_id": "L1/0_P"}
    rows = _a1_rows("ok", [{}])
    rows += _a1_rows(
        "precision",
        [{"tf32-admissible": {"e": 3e-6, "tf32_applied": False, "reason": "exceeds-T"}}],
    )
    rows += _a1_rows(
        "exact",
        [
            {
                "e_r32_device": 0.0,
                "e_r32_cpu": 0.0,
                "tf32-admissible": {"e": 0.0, "tf32_applied": False, "reason": ""},
            }
        ],
    )
    rows += _a1_rows(
        "fault", [{"tf32-admissible": {"e": 1e-3, "tf32_applied": False, "reason": "exceeds-T"}}]
    )
    rows += _a1_rows("raised", [{"candidate_raised": True}])
    rows += _a1_rows("unref", [{"admissible": False}])
    result = calibrate(rows, table, [f"L1/{i}_P" for i in range(6)])
    status = {k: v["status"] for k, v in result["kernels"].items()}
    assert status == {
        "ok": "member",
        "precision": "member",
        "exact": "member",
        "fault": "fault-candidate-error",
        "raised": "fault-candidate-raised",
        "unref": "excluded-unrefereeable",
    }
    assert result["kernels"]["precision"]["required_multiplier"] == pytest.approx(30.0)
    assert (result["multiplier"], result["multiplier_raised"]) == (32, True)
    assert result["fault_candidates"] == ["fault", "raised"]
    assert result["audit_version"]["multiplier"] == 32


def test_audit_hole_replay_classifies_gate_rejections() -> None:
    from harness.q1 import problems as problem_lib
    from harness.q1 import shapes
    from harness.q1.audit import replay
    from harness.q1.gates import gate_c

    problem_id = "L1/9001_SyntheticReLU"
    source = fx.PROBLEMS[problem_id]
    analysis = problem_lib.analyze_problem(problem_id, source)

    def input_bytes(overrides: dict[str, int]) -> int:
        variant = problem_lib.override_constants(source, analysis, overrides)
        return int(problem_lib.meta_input_summary(variant)["input_bytes"])

    manifest = {
        "problems": {
            problem_id: shapes.build_problem_manifest(
                analysis, problem_sha256="0" * 64, input_bytes=input_bytes
            )
        }
    }
    specs = gate_c.c_configs(problem_id, families=("c2",), manifest=manifest)
    double = next(s.config_id for s in specs if "S-double/D1" in s.config_id)
    requests = [
        {"gate": "c2", "config_id": double},
        {"gate": "a", "config_id": "native/trials-5/seed-42", "trials": [0]},
    ]

    def classify(name: str) -> dict[str, str]:
        import json
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(manifest, handle)
        outcomes = replay.run_replays(
            problem_id,
            source,
            str(fx.KERNELS[name]["source"]),
            replicate_seed=42,
            device=torch.device("cpu"),
            rejections=requests,
            manifest_path=handle.name,
        )
        return {o.details["rejecting_gate"]: o.details["classification"] for o in outcomes}

    assert classify("relu_correct") == {"c2": "false-reject-by-gate", "a": "false-reject-by-gate"}
    assert classify("relu_native_only")["c2"] == "audit-hole"
    assert classify("relu_refuses_shapes")["c2"] == "false-reject-by-gate"  # refusal (D14)
