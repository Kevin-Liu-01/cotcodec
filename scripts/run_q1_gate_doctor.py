#!/usr/bin/env python3
"""CPU doctor for the Q1 gate stack: gates (a)-(c), the audit, runner and journal.

Runs entirely on CPU tensors with synthetic fixtures (``harness/q1/doctor_fixtures.py``)
and Triton kernels under ``TRITON_INTERPRET=1``. It refuses to start when a
GPU is visible. Every work item goes through the real runner (one subprocess
per item, watchdog, append-only journal), then the doctor checks:

1. every asserted verdict in the fixture table (gates, audit channels, tiers);
2. gate (a)'s transcription against the verbatim vendored KernelBench@44130946
   ``run_and_check_correctness`` (synchronize shimmed to a no-op on CPU);
3. gate b2's coverage rule on synthetic profiler tables, and b1 against the
   unmodified KernelGYM ``triton_detect`` when ``KERNELGYM_SRC`` is set;
4. resume: a second runner pass over the same journal runs nothing;
5. the timing harness and the audit calibration and version helpers.

Doctor numbers are synthetic-case evidence only. Output: a fresh directory
with the corpus, the journal and ``doctor_report.json``.

    TRITON_INTERPRET=1 python scripts/run_q1_gate_doctor.py --output /tmp/q1-doctor
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

os.environ.setdefault("TRITON_INTERPRET", "1")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch  # noqa: E402

from harness.q1 import doctor_fixtures as fx  # noqa: E402
from harness.q1 import problems as problem_lib  # noqa: E402
from harness.q1 import shapes  # noqa: E402
from harness.q1.audit import oracle, tiers  # noqa: E402
from harness.q1.journal import Journal  # noqa: E402
from harness.q1.runner import Runner, RunnerConfig, WorkItem  # noqa: E402
from harness.q1.schema import sha256_bytes  # noqa: E402

DOCTOR_TIMEOUTS = {"compile": 120.0, "correctness": 20.0, "timing": 120.0}


def build_corpus(root: Path) -> tuple[dict[str, Path], dict[str, Path], Path]:
    problem_paths: dict[str, Path] = {}
    for problem_id, source in fx.PROBLEMS.items():
        path = root / "problems" / problem_lib.problem_relpath(problem_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        problem_paths[problem_id] = path
    kernel_paths: dict[str, Path] = {}
    for name, spec in fx.KERNELS.items():
        path = root / "kernels" / name / "kernel.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(spec["source"]), encoding="utf-8")
        kernel_paths[name] = path
    entries = {}
    for problem_id, source in fx.PROBLEMS.items():
        analysis = problem_lib.analyze_problem(problem_id, source)

        def input_bytes(overrides: dict[str, int], _s: str = source, _a: Any = analysis) -> int:
            variant = problem_lib.override_constants(_s, _a, overrides)
            return int(problem_lib.meta_input_summary(variant)["input_bytes"])

        entries[problem_id] = shapes.build_problem_manifest(
            analysis, problem_sha256=sha256_bytes(source.encode()), input_bytes=input_bytes
        )
    manifest_path = root / "shape_manifest.json"
    manifest_path.write_text(
        json.dumps({"schema": shapes.MANIFEST_SCHEMA, "problems": entries}, indent=1),
        encoding="utf-8",
    )
    return problem_paths, kernel_paths, manifest_path


def work_items(
    problem_paths: dict[str, Path], kernel_paths: dict[str, Path], manifest_path: Path
) -> list[WorkItem]:
    items = []
    for name, spec in fx.KERNELS.items():
        problem_id = str(spec["problem"])
        for gate in fx.ONLY_GATES.get(name, fx.DEFAULT_GATES):
            options: dict[str, Any] = {}
            if gate in {"c", "A3"}:
                options["manifest_path"] = str(manifest_path)
            items.append(
                WorkItem(
                    kernel_id=f"doctor-{name}",
                    kernel_path=str(kernel_paths[name]),
                    problem_id=problem_id,
                    gate=gate,
                    seed=42,
                    problem_source_path=str(problem_paths[problem_id]),
                    options=options,
                )
            )
    items.append(
        WorkItem(
            kernel_id="doctor-relu_correct",
            kernel_path=str(kernel_paths["relu_correct"]),
            problem_id="L1/9001_SyntheticReLU",
            gate="timing",
            seed=42,
            problem_source_path=str(problem_paths["L1/9001_SyntheticReLU"]),
            options={"rounds": 8, "warmup": 2, "resamples": 500},
        )
    )
    return items


def index_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """(kernel, gate) -> the row a verdict is read from (primary policy aggregates)."""
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        kernel = row["kernel_id"].removeprefix("doctor-")
        gate, config = row["gate"], row["config_id"]
        if gate in {"A1", "A2", "A3"}:
            primary_aggregate = config == "aggregate" and row["tf32_policy"] == "tf32-admissible"
            if primary_aggregate or config.startswith("item/"):
                index[(kernel, gate)] = row
        elif gate in {"c1", "c2", "c3", "c_1e-2", "c_kbv_raw"}:
            if config == "aggregate":
                index[(kernel, gate)] = row
        elif gate == "c" and config.startswith("item/"):
            for family in ("c1", "c2", "c3"):
                index[(kernel, family)] = row
        else:
            index[(kernel, gate)] = row
    return index


def check_expectations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = index_rows(rows)
    results = []
    for name, spec in fx.KERNELS.items():
        expect = dict(spec["expect"])  # type: ignore[arg-type]
        tier_expect = expect.pop("tiers", {})
        for gate, wanted in expect.items():
            row = index.get((name, gate))
            got = row["verdict"] if row else "missing"
            results.append(
                {
                    "kernel": name,
                    "gate": gate,
                    "expected": wanted,
                    "got": got,
                    "ok": wanted is None or got == wanted,
                }
            )
        if tier_expect:
            channels = {
                ch: index.get((name, ch), {}).get("verdict", "error")
                for ch in ("A1", "A2", "A3", "A4")
            }
            got_tiers = tiers.tier_verdicts(channels)
            for tier, wanted in tier_expect.items():
                results.append(
                    {
                        "kernel": name,
                        "gate": f"tier:{tier}",
                        "expected": wanted,
                        "got": got_tiers[tier],
                        "ok": got_tiers[tier] == wanted,
                    }
                )
    return results


def gate_a_differential(problem_paths: dict[str, Path]) -> list[dict[str, Any]]:
    from harness.q1.gates.gate_a import run_gate_a, upstream_run_and_check_correctness_cpu

    results = []
    for name in (
        "relu_correct",
        "relu_removed",
        "relu_cached",
        "rowsum_tail_drop",
        "rowsum_correct",
        "ce_torch_control",
        "argmax_last_tie",
    ):
        spec = fx.KERNELS[name]
        problem_source = problem_paths[str(spec["problem"])].read_text(encoding="utf-8")
        ours = run_gate_a(problem_source, str(spec["source"]), device="cpu").verdict
        upstream = upstream_run_and_check_correctness_cpu(problem_source, str(spec["source"]))
        results.append(
            {
                "kernel": name,
                "ours": ours,
                "upstream_correctness": upstream,
                "ok": (ours == "accept") == upstream,
            }
        )
    return results


def b2_coverage_checks() -> list[dict[str, Any]]:
    from harness.q1.gates.gate_b import coverage

    cases = [
        (
            ["relu_kernel grid=(4,) module=temp_module"],
            [{"name": "relu_kernel"}, {"name": "aten::sum"}],
            False,
        ),
        (["relu_kernel grid=(4,)"], [{"name": "aten::relu"}, {"name": "aten::sum"}], True),
        (["relu_kernel grid=(4,)"], [], False),
        (["Add grid=None"], [{"name": "aten::add"}], False),  # substring match, as released
    ]
    out = []
    for captures, rows, decoy in cases:
        got = coverage(captures, rows)["decoy"]
        out.append(
            {
                "captures": captures,
                "rows": [r["name"] for r in rows],
                "expected_decoy": decoy,
                "got": got,
                "ok": got == decoy,
            }
        )
    return out


def b1_upstream_differential(problem_paths: dict[str, Path]) -> list[dict[str, Any]] | str:
    clone = os.environ.get("KERNELGYM_SRC")
    if not clone:
        return "skipped: KERNELGYM_SRC not set"
    from harness.q1.gates import b_native
    from harness.q1.gates.common import load_candidate, load_reference, set_seed
    from harness.q1.gates.gate_b import detect_launches

    upstream = b_native.load_triton_detect_standalone(b_native.resolve_clone(clone))
    out = []
    for name in ("relu_correct", "relu_identity_control", "relu_decoy_launch", "relu_removed"):
        spec = fx.KERNELS[name]
        source = problem_paths[str(spec["problem"])].read_text(encoding="utf-8")
        _, get_init_inputs, get_inputs = load_reference(source)
        loaded = load_candidate(str(spec["source"]))
        try:
            set_seed(42)
            model = loaded.model_class(*get_init_inputs())
            set_seed(42)
            inputs = get_inputs()
            ours, _, _ = detect_launches(model, inputs, device=torch.device("cpu"))
            theirs, _ = upstream.detect_triton_usage_for_module(
                model, *inputs, warmup=1, steps=1, use_cuda=False, return_matches=True
            )
        finally:
            loaded.cleanup()
        out.append(
            {"kernel": name, "ours": ours, "upstream": bool(theirs), "ok": ours == bool(theirs)}
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--slots", type=int, default=8)
    args = parser.parse_args(argv)
    if torch.cuda.is_available():
        print("FAIL: a GPU is visible; the doctor's fixtures are CPU-only", file=sys.stderr)
        return 2
    if os.environ.get("TRITON_INTERPRET") != "1":
        print("FAIL: TRITON_INTERPRET must be 1", file=sys.stderr)
        return 2
    if args.output.exists() and any(args.output.iterdir()):
        print(
            f"FAIL: {args.output} exists and is not empty; use a fresh directory", file=sys.stderr
        )
        return 2
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    problem_paths, kernel_paths, manifest_path = build_corpus(args.output / "corpus")
    items = work_items(problem_paths, kernel_paths, manifest_path)
    config = RunnerConfig(
        journal_path=args.output / "journal.jsonl",
        slots=["cpu"] * args.slots,
        timing_slots=["cpu-timing"],
        timeouts=DOCTOR_TIMEOUTS,
        extra_env={"TRITON_INTERPRET": "1"},
        health_check=False,
        workdir=args.output / "items",
    )
    (args.output / "items").mkdir()
    first = Runner(config).run(items)
    second = Runner(config).run(items)
    journal = Journal(config.journal_path)
    rows = journal.final_rows()
    _, invalid_lines = journal.read()
    report: dict[str, Any] = {
        "doctor": "q1-gate-doctor/1",
        "torch": torch.__version__,
        "triton_interpret": os.environ.get("TRITON_INTERPRET"),
        "items": len(items),
        "first_pass": first,
        "resume_pass": second,
        "invalid_journal_lines": invalid_lines,
        "expectations": check_expectations(rows),
        "gate_a_vs_upstream_44130946": gate_a_differential(problem_paths),
        "b2_coverage_rule": b2_coverage_checks(),
        "b1_vs_upstream_kernelgym": b1_upstream_differential(problem_paths),
        "calibration": {
            "no_raise": oracle.calibrate_multiplier([3.0, 15.9]),
            "raise_to_64": oracle.calibrate_multiplier([3.0, 40.0]),
        },
        "audit_version": tiers.audit_version_hash(multiplier=16, multiplier_raised=False),
    }
    timing_rows = [r for r in rows if r["gate"] == "timing"]
    report["timing"] = timing_rows[0]["details"] if timing_rows else None
    checks = {
        "expectations": all(r["ok"] for r in report["expectations"]),
        "gate_a_differential": all(r["ok"] for r in report["gate_a_vs_upstream_44130946"]),
        "b2_coverage_rule": all(r["ok"] for r in report["b2_coverage_rule"]),
        "b1_differential": isinstance(report["b1_vs_upstream_kernelgym"], str)
        or all(r["ok"] for r in report["b1_vs_upstream_kernelgym"]),
        "resume_runs_nothing": second["run"] == 0 and second["skipped"] == len(items),
        "every_item_final": first["run"] == len(items) and first["left_in_queue"] == 0,
        "journal_clean": invalid_lines == 0,
        "calibration": report["calibration"]["no_raise"] == (16, False)
        and report["calibration"]["raise_to_64"] == (64, True),
        "timing_ran": bool(timing_rows) and timing_rows[0]["details"].get("tf32") is not None,
    }
    report["checks"] = checks
    report["status"] = "PASS" if all(checks.values()) else "FAIL"
    report["wall_seconds"] = round(time.time() - started, 1)
    (args.output / "doctor_report.json").write_text(
        json.dumps(report, indent=1, sort_keys=True, default=str), encoding="utf-8"
    )
    failed = [r for r in report["expectations"] if not r["ok"]]
    print(
        json.dumps(
            {
                "status": report["status"],
                "checks": checks,
                "failed": failed,
                "wall_seconds": report["wall_seconds"],
            },
            indent=1,
            default=str,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
