"""Q1 end to end on CPU: substrates -> mutants and controls -> gates (a)-(c) and the audit.

Every step runs the components' own code:

1. **Substrates.** The S1 TorchInductor ReLU is converted from its committed
   codegen record (``harness.q1.substrates.inductor_convert``); the S2 Triton
   tutorial fused softmax is built from the vendored upstream file
   (``harness.q1.substrates.s2_catalog``). S1 kernels target CUDA: they refuse
   non-CUDA tensors and allocate with ``empty_strided_cuda``. This test applies
   :func:`cpu_port`, four exact string edits to the host code (device code is
   untouched), recorded as a ``q1-test-cpu-port`` transformation. The port is a
   test fixture only and never enters a corpus.
2. **Mutator.** Pool, selection (CPU preview, no compile filter) and the hack
   controls (``harness.q1.mutate.corpus``) on those substrates.
3. **Gates and audit.** ``a``, ``a_1e-3``, ``b1``, ``c`` and ``A1``-``A4`` through
   the real runner (one worker process per item, phase watchdog, append-only
   journal) with Triton kernels under ``TRITON_INTERPRET=1`` on CPU tensors.
   Problems are the pinned KernelBench files with ``batch_size`` and ``dim``
   shrunk to 16 and 1024 by the core's constant override; gate (c) and A3 use
   a shape manifest built from them by the core's own rules. Triton 3.6's
   interpreter cannot run Inductor output unaided (it hands grid callables
   interpreter tensors, and NumPy 2.5 rejects its ``int()`` on 1-element
   arrays), so each worker starts the substrate owner's interpreter-check shims
   (``harness.q1.substrates.admission._InterpreterLaunches``) from a test-only
   ``sitecustomize``. Compiled Triton on a GPU needs neither.
4. **Analysis.** Every journal row validates under the shared schema with a
   known gate id and the worker's ``code_sha256``; rows compose into the
   ladder and the audit tiers; every control expectation holds except those
   that need gate ``b2``, which reads CUDA profiler events and cannot run on
   CPU (``b`` and ``c`` are checked as ``a and b1`` and ``b and c1 and c2 and
   c3``, which is what they reduce to when ``b2`` accepts).

The fixtures run only without a visible GPU (decisions D3, D7, D12).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("TRITON_INTERPRET", "1")
torch = pytest.importorskip("torch")
pytest.importorskip("triton")
pytest.importorskip("scipy")
if torch.cuda.is_available():  # pragma: no cover - CPU-only fixtures
    pytest.skip("the integration fixtures are CPU-only", allow_module_level=True)

from harness.q1 import analysis, problems, schema, shapes, versions  # noqa: E402
from harness.q1.journal import Journal  # noqa: E402
from harness.q1.mutate import corpus  # noqa: E402
from harness.q1.runner import Runner, RunnerConfig, WorkItem  # noqa: E402
from harness.q1.substrates import inductor_convert, s2_catalog, sources  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "tests" / "fixtures" / "q1_substrates" / "L1__19_ReLU.json"
SHRUNK = {"batch_size": 16, "dim": 1024}
PROBLEM_IDS = ("L1/19_ReLU", "L1/23_Softmax")
S1_RELU = "s1-inductor-L1-19_ReLU"
S2_SOFTMAX = "s2-tutorial-fused-softmax-L1-23_Softmax"
SCORED_GATES = ("a", "a_1e-3", "b1", "c", "A1", "A2", "A3", "A4")

#: Host-code edits that let the CUDA-targeting S1 wrapper run on CPU tensors.
CPU_PORT = (
    ("value.device.type != 'cuda'", "value.device.type != 'cpu'"),
    (
        "empty_strided_cuda = torch._C._dynamo.guards._empty_strided_cuda",
        "empty_strided_cuda = lambda size, stride, dtype: torch.empty_strided("
        "size, stride, dtype=dtype, device='cpu')",
    ),
    ("torch.cuda._DeviceGuard(device_index)", "__import__('contextlib').nullcontext()"),
    ("torch.cuda.set_device(device_index)", "None"),
)

#: Deterministic mutants and what each gate must say, from their semantics on
#: the shrunk problems (inputs are torch.rand, so values lie in [0, 1)).
MUTANTS = {
    (S1_RELU, "relu-max-zero-first-remove"): {
        # identity on [0, 1): invisible to gate (a); D4 negation (c1) and the
        # audit's signed draws (A2) expose it (the KBV H.1 analogue)
        "a": "accept",
        "c": "reject",
        "A1": "accept",
        "A2": "reject",
        "G": "reject",
    },
    (S1_RELU, "negate-store"): {"a": "reject", "c": "reject", "G": "reject"},
    (S1_RELU, "store-scale-nudge"): {
        # x 0.9999: inside every gate tolerance, beyond the fp64 audit's T
        "a": "accept",
        "a_1e-3": "accept",
        "c": "accept",
        "A1": "reject",
        "G": "reject",
    },
    (S2_SOFTMAX, "softmax-max-subtraction-remove"): {
        # exact up to rounding on [0, 3); overflows on A2's x100 and spiky draws
        "a": "accept",
        "c": "accept",
        "A2": "reject",
        "G": "reject",
    },
    (S2_SOFTMAX, "negate-store"): {
        # softmax over 1024 columns is about 1e-3 everywhere, below gate (a)'s
        # absolute tolerance 1e-2, so even a negated output passes it; the 1e-3
        # gates and the audit see it (at the native 393,216 columns, about 2.5e-6)
        "a": "accept",
        "a_1e-3": "reject",
        "c": "reject",
        "G": "reject",
    },
}

#: Work gates needed to evaluate each control expectation (b2 cannot run on CPU).
NEEDS = {
    "a": {"a"},
    "b1": {"b1"},
    "b": {"a", "b1"},
    "c1": {"c"},
    "c2": {"c"},
    "c3": {"c"},
    "c": {"a", "b1", "c"},
    "A1": {"A1"},
    "A2": {"A2"},
    "A3": {"A3"},
    "A4": {"A4"},
    "audit_N": {"A1", "A2", "A4"},
    "audit_G": {"A1", "A2", "A3", "A4"},
    "audit_G_strict": {"A1", "A2", "A3", "A4"},
}
NOT_ON_CPU = {"b2", "b_native"}

#: Loaded by every worker through PYTHONPATH (test only; see the module docstring).
INTERPRETER_SITECUSTOMIZE = """# Q1 CPU integration test: Triton interpreter shims for workers.
import os

if os.environ.get("TRITON_INTERPRET") == os.environ.get("Q1_TEST_INTERPRETER_SHIMS") == "1":
    from harness.q1.substrates.admission import _InterpreterLaunches

    _InterpreterLaunches().__enter__()
"""


def cpu_port(text: str) -> str:
    for old, new in CPU_PORT:
        assert old in text, f"S1 converter output changed; update the CPU port: {old!r}"
        text = text.replace(old, new)
    return text


def _conjoin(verdicts: list[str]) -> str:
    for verdict in ("reject", "error"):
        if verdict in verdicts:
            return verdict
    return "accept"


def cpu_verdict(entry: dict, gate: str) -> str:
    """``analysis.composed_verdict`` with ``b`` and ``c`` composed as if b2 accepted."""
    gates, ladder = entry["gates"], entry["ladder"]
    if gate == "b":
        return _conjoin([ladder["a"], gates.get("b1", "missing")])
    if gate == "c":
        families = [gates.get(name, "missing") for name in ("c1", "c2", "c3")]
        return _conjoin([cpu_verdict(entry, "b"), *families])
    if gate == "G":
        return entry["tiers"][analysis.PRIMARY_POLICY]["G"]
    return analysis.composed_verdict(entry, gate)


def _shrunk_problems(root: Path) -> tuple[dict[str, Path], Path]:
    paths, entries = {}, {}
    for problem_id in PROBLEM_IDS:
        source = problems.load_problem_source(problem_id)
        native = problems.analyze_problem(problem_id, source)
        text = problems.override_constants(source, native, SHRUNK)
        path = root / "kernelbench" / problems.problem_relpath(problem_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        paths[problem_id] = path
        shrunk = problems.analyze_problem(problem_id, text)

        def input_bytes(overrides, _text=text, _analysis=shrunk) -> int:
            variant = problems.override_constants(_text, _analysis, overrides)
            return int(problems.meta_input_summary(variant)["input_bytes"])

        entries[problem_id] = shapes.build_problem_manifest(
            shrunk, problem_sha256=schema.sha256_bytes(text.encode()), input_bytes=input_bytes
        )
    manifest = root / "shape_manifest.json"
    manifest.write_text(json.dumps({"schema": shapes.MANIFEST_SCHEMA, "problems": entries}))
    return paths, manifest


def _substrates(root: Path) -> None:
    root.mkdir(parents=True)
    converted = inductor_convert.convert_record(json.loads(RECORD.read_text()))
    directory = root / converted.substrate_id
    directory.mkdir()
    files = converted.files()
    files["kernel.py"] = cpu_port(files["kernel.py"])
    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8")
    substrate = dict(converted.substrate_json)
    substrate["transformations"] = [
        *substrate["transformations"],
        {
            "name": "q1-test-cpu-port",
            "detail": "test fixture only: host code accepts CPU tensors and allocates on CPU "
            "(tests/test_q1_integration_cpu.py::CPU_PORT); device code unchanged",
        },
    ]
    substrate["files"] = [
        {"path": e["path"], "sha256": schema.sha256_bytes(files[e["path"]].encode())}
        if e["path"] in files
        else e
        for e in substrate.get("files", [])
    ]
    (directory / "substrate.json").write_text(json.dumps(schema.validate_substrate(substrate)))
    rows = s2_catalog.build_all(
        sources.VENDORED_SOURCES_ROOT,
        problems.PROBLEMS_ROOT,
        root,
        only=["tutorial-fused-softmax"],
    )
    assert [row["status"] for row in rows] == ["built"]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    base = tmp_path_factory.mktemp("q1-e2e")
    problem_paths, manifest_path = _shrunk_problems(base)
    _substrates(base / "substrates")
    corpus.build_pool(base / "substrates", base / "pool")
    corpus.select(
        base / "pool",
        base / "substrates",
        base / "mutants",
        require_compile=False,
        controls_root=base / "controls-mutants",
    )
    corpus.build_controls(base / "substrates", base / "kernelbench", base / "controls-hacks")
    roots = [base / name for name in ("substrates", "mutants", "controls-mutants")]
    roots.append(base / "controls-hacks")
    table = analysis.kernel_table(roots)

    chosen: dict[str, set[str]] = {}
    for kernel_id, facts in table.items():
        if facts["kind"] == "substrate":
            chosen[kernel_id] = set(SCORED_GATES)
        elif facts["kind"] == "mutant":
            key = (facts["parent_substrate_id"], facts["operator"])
            if key in MUTANTS:
                chosen[kernel_id] = set(SCORED_GATES)
        else:
            gates = set()
            for gate in facts["expected"]:
                if gate not in NOT_ON_CPU:
                    gates |= NEEDS[gate]
            chosen[kernel_id] = gates
    kernels = {k.kernel_id: k for root in roots for k in schema.iter_kernel_dirs(root)}
    items = [
        WorkItem(
            kernel_id=kernel_id,
            kernel_path=str(kernels[kernel_id].kernel_path),
            problem_id=table[kernel_id]["problem_id"],
            gate=gate,
            seed=42,
            problem_source_path=str(problem_paths[table[kernel_id]["problem_id"]]),
            options={"manifest_path": str(manifest_path)} if gate in {"c", "A3"} else {},
        )
        for kernel_id, gates in sorted(chosen.items())
        for gate in sorted(gates)
    ]
    (base / "items").mkdir()
    (base / "pyshim").mkdir()
    (base / "pyshim" / "sitecustomize.py").write_text(INTERPRETER_SITECUSTOMIZE)
    config = RunnerConfig(
        journal_path=base / "journal.jsonl",
        slots=["cpu"] * min(16, os.cpu_count() or 2),
        timeouts={"compile": 300.0, "correctness": 900.0, "timing": 60.0},
        extra_env={
            "TRITON_INTERPRET": "1",
            "Q1_TEST_INTERPRETER_SHIMS": "1",
            "PYTHONPATH": str(base / "pyshim"),
        },
        health_check=False,
        workdir=base / "items",
    )
    summary = Runner(config).run(items)
    journal = Journal(config.journal_path)
    return {
        "base": base,
        "roots": roots,
        "table": table,
        "chosen": chosen,
        "items": items,
        "summary": summary,
        "journal": journal,
        "rows": journal.final_rows(),
        "composed": analysis.compose(journal.final_rows()),
    }


def _mutant_id(run: dict, parent: str, operator: str) -> str:
    matches = [
        k
        for k, v in run["table"].items()
        if v["kind"] == "mutant" and (v["parent_substrate_id"], v["operator"]) == (parent, operator)
    ]
    assert len(matches) == 1, (parent, operator, matches)
    return matches[0]


def test_every_item_ran_once_without_infrastructure_failures(run: dict) -> None:
    summary = run["summary"]
    assert summary["run"] == len(run["items"]) and summary["left_in_queue"] == 0
    assert summary["timeouts"] == 0 and summary["crashes"] == 0, summary
    status = run["journal"].status()
    assert {item.key for item in run["items"]} == set(status)
    assert all(entry["final"] for entry in status.values())
    _, invalid = run["journal"].read()
    assert invalid == 0


def test_verdict_rows_follow_the_shared_schema(run: dict) -> None:
    rows = schema.read_verdict_rows(run["journal"].path)
    assert rows
    run_ids = {row["run_id"] for row in rows}
    assert len(run_ids) == 1
    for row in rows:
        schema.validate_verdict_row(row, known_gates_only=True)
        assert row["kernel_id"] in run["table"]
        assert row["seed"] == 42 and row["attempt"] == 1
        assert row["code_sha256"] == versions.row_code_sha256(row["gate"])
        assert row["gpu_seconds"] == 0.0  # CPU slots never bill GPU time
        if row["gate"] in {"A1", "A2", "A3"} and row["config_id"] == "aggregate":
            assert row["tf32_policy"] in {"tf32-admissible", "strict-fp32"}
        if row["gate"] in {"a", "a_1e-3", "b1"}:
            assert row["tf32_policy"] == "torch-default"
    finals = [row for row in rows if row["details"].get("item_final")]
    assert len(finals) == len(run["items"])
    assert {row["gate"] for row in rows} >= {"a", "b1", "c1", "c2", "c3", "A1", "A2", "A3", "A4"}


def test_substrates_are_correct_under_every_gate_and_the_primary_tier(run: dict) -> None:
    for substrate in (S1_RELU, S2_SOFTMAX):
        entry = run["composed"][substrate]
        for gate in ("a", "a_1e-3", "b1", "c1", "c2", "c3"):
            assert analysis.composed_verdict(entry, gate) == "accept", (substrate, gate)
        assert cpu_verdict(entry, "c") == "accept"
        tiers = entry["tiers"][analysis.PRIMARY_POLICY]
        assert tiers["N"] == "accept" and tiers["G"] == "accept", (substrate, tiers)
    # The S1 wrapper refuses size 1 before any launch (Dynamo's 0/1 specialisation):
    # A3/lead1 is a refusal, non-general under tier G and a fault under G-strict.
    s1 = run["composed"][S1_RELU]
    assert s1["audit"][analysis.PRIMARY_POLICY]["A3"] == "refuse"
    assert s1["tiers"][analysis.PRIMARY_POLICY]["G-strict"] == "reject"
    s2 = run["composed"][S2_SOFTMAX]
    assert s2["tiers"][analysis.PRIMARY_POLICY]["G-strict"] == "accept"


@pytest.mark.parametrize("key", sorted(MUTANTS), ids=lambda k: f"{k[0][:14]}:{k[1]}")
def test_mutants_get_their_semantic_verdicts(run: dict, key: tuple[str, str]) -> None:
    entry = run["composed"][_mutant_id(run, *key)]
    got = {gate: cpu_verdict(entry, gate) for gate in MUTANTS[key]}
    assert got == MUTANTS[key]


def test_every_control_expectation_holds_on_cpu(run: dict) -> None:
    table = {k: v for k, v in run["table"].items() if v["kind"] == "control"}
    assert len(table) == 16  # 11 kinds on the ReLU, 4 on the softmax, 1 mutant control
    failed = []
    for control_id, facts in table.items():
        entry = run["composed"][control_id]
        for gate, expected in facts["expected"].items():
            if gate in NOT_ON_CPU:
                continue
            got = cpu_verdict(entry, gate)
            if got != expected:
                failed.append((control_id, gate, expected, got))
    assert not failed, failed
    # The analysis's own check sees the same cells; only b2 and the b2-composed
    # gates (b and c reported "error" while b2 is absent) may differ.
    checks = analysis.control_checks(run["composed"], table)
    for cell in checks["failed"]:
        assert cell["gate"] in NOT_ON_CPU | {"b", "c"}, cell


def _with_b2_failing_open(rows: list[dict]) -> list[dict]:
    """b2 needs CUDA profiler events, so the CPU run has no b2 item. Record it as an
    ``error`` row per kernel, which the ladder counts as accept (the released check
    fails open), so b = a and b1 and every gate referees the same kernels."""
    extra = [
        schema.make_verdict_row(
            kernel_id=kernel,
            gate="b2",
            config_id="native/seed-42",
            verdict="error",
            tf32_policy="torch-default",
            gpu_seconds=0.0,
            details={"reason": "not-run-on-cpu", "item_key": f"{kernel}|b2|seed-42"},
            seed=42,
        )
        for kernel in sorted({row["kernel_id"] for row in rows})
    ]
    return [*rows, *extra]


def test_metrics_and_report_run_on_the_journal(run: dict, tmp_path: Path) -> None:
    scored = {k: v for k, v in run["table"].items() if k in run["composed"]}
    problem_of = {k: v["problem_id"] for k, v in scored.items()}
    composed = analysis.compose(_with_b2_failing_open(run["rows"]), problem_of=problem_of)
    result = analysis.metrics(composed, scored, resamples=200)
    # every mutant's parent passes the primary audit, so the parent filter keeps all five
    assert result["counts"]["mutants_excluded"] == {}
    # all five chosen mutants are witnessed; gate (a) rejects only the S1 negation
    assert result["counts"]["witnessed"] == len(MUTANTS)
    assert result["gates"]["a"]["MS"]["k"] == 1 and result["gates"]["a"]["MS"]["n"] == 5
    assert result["gates"]["a_1e-3"]["MS"]["k"] == 2
    assert result["counts"]["correct_substrates"] == 2
    assert result["gates"]["a"]["FRR"]["k"] == 0 and result["gates"]["a"]["FRR"]["n"] == 2
    sys.path.insert(0, str(ROOT))
    from scripts import report_q1_stage0

    output = tmp_path / "report.json"
    argv = ["--journal", str(run["journal"].path), "--output", str(output)]
    for root in run["roots"]:
        argv += ["--corpus", str(root)]
    assert report_q1_stage0.main([*argv, "--seeds", "42", "--resamples", "50"]) == 0
    report = json.loads(output.read_text())
    assert report["splits"]["s1_split_sha256"] == versions.version_card()["s1_split_sha256"]
    replicate = report["replicates"]["42"]
    assert replicate["controls"][analysis.PRIMARY_POLICY]["cells"] > 0
    assert set(replicate["metrics"]) == {"test", "dev"}


def test_trim_plan_driver_and_report_on_the_cpu_journal(run: dict, tmp_path: Path) -> None:
    """Second review, findings 3 and 8: the trimming rule's plan is computed from the
    corpus (seeded frames, samples and schedule), the Stage 0 driver plans the same
    thing and refuses to score without its budget, and the report reads the plan
    for the trimmed weights, the control schedule and the pilot-exposure analysis."""
    from harness.q1 import trim

    sys.path.insert(0, str(ROOT))
    from scripts import report_q1_stage0, run_q1_stage0

    rule = {**trim.TRIM_RULE, "scope_bytes": 10**13, "frr_min_units": 1, "frr_margin_units": 0}
    records = trim.records_from_corpus(run["roots"])
    kinds = {r.kernel_id: r for r in records}
    assert kinds[S2_SOFTMAX].half == "evaluation" and kinds[S1_RELU].half == "calibration"
    record = trim.plan(records, rule=rule, exposed=trim.load_exposed())
    planned = {(i["bucket"], i["kernel_id"], i["seed"]) for i in record["items"]}
    assert ("P1", S2_SOFTMAX, 42) in planned and ("P5", S2_SOFTMAX, 44) in planned
    # mutants of the S1-cal ReLU are never sampled; the softmax's are, as prefixes
    sampled = {k for f in record["mutant_sample"].values() for k in f["test_quota"]}
    assert sampled and all(kinds[k].parent == S2_SOFTMAX for k in sampled)
    assert all(
        f["test_quota"] == record["mutant_frames"][family]["test"][: len(f["test_quota"])]
        for family, f in record["mutant_sample"].items()
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(record))
    # The driver (registered rule) plans on the CPU and refuses to score over budget.
    out = tmp_path / "stage0"
    argv = ["--output", str(out), "--seeds", "42", "43", "44"]
    for root in run["roots"]:
        argv += ["--corpus", str(root)]
    assert run_q1_stage0.main([*argv, "--plan-only"]) == 0
    driver_plan = json.loads((out / "plan.json").read_text())
    assert driver_plan["plan_sha256"] == trim.plan_digest(driver_plan)
    budget = [
        "--expected-plan-sha256",
        driver_plan["plan_sha256"],
        "--stage0-spent-gpu-hours",
        "0.899",
        "--job-cap-gpu-hours",
        "7.0",
        "--reserve-gpu-hours",
        "1.5",
        "--budget-minutes",
        "420",
    ]
    assert run_q1_stage0.main([*argv, *budget]) == 2
    assert not json.loads((out / "budget.json").read_text())["ok"]
    assert not (out / "journal.jsonl").exists()
    wrong = [*argv, *budget]
    wrong[wrong.index("--expected-plan-sha256") + 1] = "0" * 64
    assert run_q1_stage0.main(wrong) == 2
    # The lane path: the corpus as one hash-bound study artifact, unpacked beside
    # the output (a resumed job copies the output directory only), same plan.
    from harness.q1 import study_artifact

    trees = {
        root.name: study_artifact.dir_tree(root, source="q1-test", licence="mixed")
        for root in run["roots"]
    }
    artifact = tmp_path / "study-artifact.json"
    receipt = study_artifact.write(study_artifact.build(trees, repo_revision="0" * 40), artifact)
    lane = tmp_path / "lane" / "stage0"
    lane_argv = ["--output", str(lane), "--seeds", "42", "43", "44", "--plan-only"]
    lane_argv += ["--evidence", str(artifact), "--expected-evidence-sha256", receipt["sha256"]]
    for root in run["roots"]:
        lane_argv += ["--corpus", root.name]
    assert run_q1_stage0.main(lane_argv) == 0
    assert (tmp_path / "lane" / "stage0-inputs" / run["roots"][0].name).is_dir()
    assert json.loads((lane / "plan.json").read_text())["plan_sha256"] == driver_plan["plan_sha256"]
    # The report under the plan: trimmed weights, scheduled controls, sensitivity.
    output = tmp_path / "report.json"
    rargv = ["--journal", str(run["journal"].path), "--output", str(output)]
    for root in run["roots"]:
        rargv += ["--corpus", str(root)]
    rargv += ["--plan", str(plan_path), "--seeds", "42", "--resamples", "50"]
    assert report_q1_stage0.main(rargv) == 0
    report = json.loads(output.read_text())
    assert report["trim_plan_sha256"] == record["plan_sha256"]
    assert report["trim_weights"]["factors"]
    replicate = report["replicates"]["42"]
    controls = replicate["controls"][analysis.PRIMARY_POLICY]
    scheduled = trim.scheduled_controls(record)[42]
    assert set(controls["not_scheduled"]) == {
        k for k, v in run["table"].items() if v["kind"] == "control" and k not in scheduled
    }
    assert "criterion_3_FRR_c" in replicate["sensitivity_without_pilot_exposed"]
    assert "problems_at_or_above_threshold" in report["audit_tolerance"]
    assert "kernels_shifted" in replicate["sanitizer_shift"]
