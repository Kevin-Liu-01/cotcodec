#!/usr/bin/env python3
"""Build and admit the Q1 Stage 0 substrate corpus (S1 Inductor, S2 human-written Triton).

Subcommands, in pipeline order:

``s1-codegen``     Compile every admissible KernelBench L1/L2 problem with TorchInductor
                   (one subprocess per problem) and write codegen records. Needs the
                   research image; ``--mode mock-h100`` runs in a GPU-less container.
``s1-convert``     Convert records into substrate directories (pure Python).
``s2-build``       Build the S2 substrates from pinned FlagGems, Liger and Triton
                   tutorial sources (pure Python).
``check-static``   Launch-path admission by AST: plain JIT/Autotuner launches only, no
                   libentry or triton_heuristics, ModelNew present (pure Python).
``check-compile``  Compile every kernel for sm_90 without a GPU on small CPU inputs.
``check-compile-native``  The same at native shapes on the meta device (nothing runs).
``check-interp``   Run ModelNew against Model on small CPU inputs with the Triton
                   interpreter (needs torch + triton, no GPU). Build validation only.
``admit-gpu``      GPU admission: gate (b)'s launch hook must observe a launch under
                   inference_mode and enable_grad; writes ``admission_hook`` rows.
                   Runs only inside a one-GPU Slurm job.
``split``          Seeded calibration/evaluation split of S1 problems (seed 42).
``manifest``       Corpus manifest: one row per substrate with provenance and every
                   admission verdict so far.
``admission-job``  The one-GPU Slurm job: device-mode S1 codegen, conversion, S2 build,
                   static check, split, admission and manifest, all under ``--out``.
``parity``         Compare mock-H100 and device-mode codegen records (CPU).

Nothing here scores a gate or a mutant. Exit code 0 means the step ran; per-item
outcomes are in the JSONL logs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.q1.schema import parse_problem_id, problem_id_from_path  # noqa: E402
from harness.q1.substrates import admission, split  # noqa: E402
from harness.q1.substrates.sources import (  # noqa: E402
    EXCLUDED_PROBLEMS,
    LEVELS,
    VENDORED_SOURCES_ROOT,
    level_dir,
)

#: Vendored KernelBench@423217d9 problems (core owner's tree), the default problem root.
DEFAULT_KERNELBENCH_ROOT = (
    PROJECT_ROOT / "harness" / "q1" / "third_party" / "kernelbench" / "problems"
)

#: Problems whose default Inductor output calls a library GEMM or convolution are
#: recompiled with Triton templates (reviewed plan section 7(ii) for GEMMs; the
#: same rule for convolutions); the template build is kept only if Inductor's
#: deterministic choice is a Triton template.
GEMM_EXTERN_MARKERS = (
    "extern_kernels.mm(",
    "extern_kernels.bmm(",
    "extern_kernels.addmm(",
    "extern_kernels.baddbmm(",
    "extern_kernels.convolution(",
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(value, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    tmp.replace(path)


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def kernelbench_problems(kernelbench_root: Path, levels: tuple[int, ...]) -> list[tuple[str, Path]]:
    """``(problem_id, path)`` for every problem file of the given levels, sorted by id."""
    problems = []
    for level in levels:
        for path in level_dir(kernelbench_root, level).glob("*.py"):
            problem_id = problem_id_from_path(f"level{level}/{path.name}")
            problems.append((problem_id, path))
    return sorted(problems, key=lambda item: parse_problem_id(item[0])[:2])


def record_name(problem_id: str) -> str:
    return problem_id.replace("/", "__") + ".json"


# --- s1-codegen --------------------------------------------------------------------


def cmd_s1_codegen_one(args: argparse.Namespace) -> int:
    from harness.q1.substrates import inductor_codegen as codegen

    out = Path(args.out)
    folding = True

    def compile_once(gemm: bool) -> dict[str, Any]:
        nonlocal folding
        try:
            return codegen.codegen_problem(
                Path(args.problem_path),
                args.problem_id,
                mode=args.mode,
                max_autotune_gemm=gemm,
                constant_folding=folding,
            )
        except codegen.CodegenError as exc:
            # In mock mode Inductor's joint-graph constant folding evaluates small
            # CUDA constants eagerly; retry once without that pass and record it.
            if args.mode == "mock-h100" and folding and "no NVIDIA driver" in exc.detail:
                folding = False
                return codegen.codegen_problem(
                    Path(args.problem_path),
                    args.problem_id,
                    mode=args.mode,
                    max_autotune_gemm=gemm,
                    constant_folding=False,
                )
            raise

    try:
        record = compile_once(args.gemm_templates)
        if not args.gemm_templates and any(m in record["output_code"] for m in GEMM_EXTERN_MARKERS):
            first = record
            try:
                templated = compile_once(True)
                if any(k["heuristic"] == "template" for k in templated["kernels"]):
                    record = templated
                    record["gemm_retry"] = {
                        "reason": "default codegen called a library GEMM or convolution",
                        "default_kernels": [k["name"] for k in first["kernels"]],
                    }
                else:
                    record = first
                    record["gemm_retry"] = {
                        "reason": "default codegen called a library GEMM or convolution",
                        "template_error": "no Triton template selected",
                    }
            except codegen.CodegenError as exc:
                record = first
                record["gemm_retry"] = {
                    "reason": "default codegen called a library GEMM or convolution",
                    "template_error": f"{exc.reason}: {exc.detail[-500:]}",
                }
        codegen.write_record(record, out)
        return 0
    except codegen.CodegenError as exc:
        _write_json(
            out.with_suffix(".error.json"),
            {
                "problem_id": args.problem_id,
                "status": "codegen-error",
                "reason": exc.reason,
                "detail": exc.detail[-4000:],
            },
        )
        return 3


def cmd_s1_codegen(args: argparse.Namespace) -> int:
    records = Path(args.records_dir)
    records.mkdir(parents=True, exist_ok=True)
    problems = kernelbench_problems(Path(args.kernelbench_root), tuple(args.levels))
    if args.problems:
        wanted = set(args.problems)
        problems = [item for item in problems if item[0] in wanted]
        unknown = wanted - {item[0] for item in problems}
        if unknown:
            print(f"unknown problems: {sorted(unknown)}", file=sys.stderr)
            return 2
    log_rows: list[dict[str, Any]] = []
    todo = []
    for problem_id, path in problems:
        if problem_id in EXCLUDED_PROBLEMS:
            log_rows.append(
                {
                    "problem_id": problem_id,
                    "status": "excluded",
                    "reason": EXCLUDED_PROBLEMS[problem_id],
                }
            )
            continue
        target = records / record_name(problem_id)
        if target.exists() and not args.force:
            log_rows.append({"problem_id": problem_id, "status": "exists"})
            continue
        todo.append((problem_id, path, target))

    def run(item: tuple[str, Path, Path]) -> dict[str, Any]:
        problem_id, path, target = item
        target.with_suffix(".error.json").unlink(missing_ok=True)
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "s1-codegen-one",
            "--problem-path",
            str(path),
            "--problem-id",
            problem_id,
            "--out",
            str(target),
            "--mode",
            args.mode,
        ]
        started = time.monotonic()
        env = {
            **os.environ,
            "TORCHINDUCTOR_COMPILE_THREADS": "1",
            "TORCHINDUCTOR_CACHE_DIR": str(records / ".inductor-cache" / record_name(problem_id)),
        }
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=args.timeout, env=env, check=False
            )
        except subprocess.TimeoutExpired:
            return {"problem_id": problem_id, "status": "timeout", "seconds": args.timeout}
        row = {
            "problem_id": problem_id,
            "returncode": completed.returncode,
            "seconds": round(time.monotonic() - started, 2),
        }
        if completed.returncode == 0:
            row["status"] = "ok"
        elif target.with_suffix(".error.json").exists():
            error = json.loads(target.with_suffix(".error.json").read_text(encoding="utf-8"))
            row.update(status="codegen-error", reason=error["reason"])
        else:
            row.update(status="crash", reason="crash", stderr_tail=completed.stderr[-2000:])
            _write_json(
                target.with_suffix(".error.json"),
                {
                    "problem_id": problem_id,
                    "status": "crash",
                    "reason": "crash",
                    "detail": completed.stderr[-4000:],
                },
            )
        return row

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for row in pool.map(run, todo):
            log_rows.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
    _append_jsonl(records / "codegen_log.jsonl", [{**row, "mode": args.mode} for row in log_rows])
    summary: dict[str, int] = {}
    for row in log_rows:
        summary[row["status"]] = summary.get(row["status"], 0) + 1
    print(json.dumps({"summary": summary}, sort_keys=True))
    return 0


# --- s1-convert ----------------------------------------------------------------------


def write_substrate(out_root: Path, converted: Any, *, force: bool) -> Path:
    directory = out_root / converted.substrate_id
    if directory.exists() and not force:
        raise FileExistsError(f"{directory} exists; pass --force to rebuild")
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in converted.files().items():
        (directory / name).write_text(text, encoding="utf-8")
    (directory / "substrate.json").write_text(
        json.dumps(converted.substrate_json, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return directory


def cmd_s1_convert(args: argparse.Namespace) -> int:
    from harness.q1.substrates.inductor_convert import ConversionError, convert_record

    records = Path(args.records_dir)
    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(records.glob("L*__*.json")):
        if path.name.endswith(".error.json"):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        problem_id = record["problem_id"]
        try:
            converted = convert_record(record)
        except ConversionError as exc:
            rows.append(
                {
                    "problem_id": problem_id,
                    "status": "conversion-error",
                    "reason": exc.reason,
                    "detail": exc.detail[:500],
                }
            )
            continue
        write_substrate(out_root, converted, force=args.force)
        rows.append(
            {
                "problem_id": problem_id,
                "status": "converted",
                "substrate_id": converted.substrate_id,
                "triton_coverage": converted.build_json["triton_coverage"],
                "kernels": len(converted.build_json["kernels"]),
            }
        )
    for path in sorted(records.glob("*.error.json")):
        error = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "problem_id": error["problem_id"],
                "status": "codegen-error",
                "reason": error["reason"],
            }
        )
    _write_json(out_root / "s1_build_log.json", {"rows": rows})
    summary: dict[str, int] = {}
    for row in rows:
        key = row["status"] if row["status"] == "converted" else f"{row['status']}:{row['reason']}"
        summary[key] = summary.get(key, 0) + 1
    print(json.dumps({"summary": summary}, indent=1, sort_keys=True))
    return 0


# --- s2-build ----------------------------------------------------------------------


def cmd_s2_build(args: argparse.Namespace) -> int:
    from harness.q1.substrates import s2_catalog

    out_root = Path(args.out_root)
    rows = s2_catalog.build_all(
        Path(args.sources_root), Path(args.kernelbench_root), out_root, force=args.force
    )
    _write_json(out_root / "s2_build_log.json", {"rows": rows})
    print(json.dumps(rows, indent=1, sort_keys=True))
    return 0 if all(row["status"] == "built" for row in rows) else 1


# --- checks --------------------------------------------------------------------------


def _substrate_dirs(root: Path, only: list[str] | None) -> list[Path]:
    dirs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "substrate.json").exists())
    if only:
        dirs = [p for p in dirs if p.name in set(only)]
    return dirs


def cmd_check_static(args: argparse.Namespace) -> int:
    rows = [admission.static_check(path) for path in _substrate_dirs(Path(args.root), args.only)]
    _write_json(Path(args.root) / "check_static.json", {"rows": rows})
    failed = [row for row in rows if row["verdict"] != "pass"]
    print(
        json.dumps(
            {"checked": len(rows), "failed": [r["substrate_id"] for r in failed]}, sort_keys=True
        )
    )
    return 0


def _run_cpu_check(args: argparse.Namespace, check: str) -> int:
    """Run ``admission.<check>`` per substrate in its own subprocess (no GPU)."""
    root = Path(args.root)
    rows = []
    function = {
        "compile": "compile_check",
        "compile-native": "native_compile_check",
        "interp": "interpreter_check",
    }[check]

    def run(path: Path) -> dict[str, Any]:
        command = [
            sys.executable,
            "-c",
            "import json, sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(PROJECT_ROOT)!r}); "
            "from harness.q1.substrates import admission; "
            f"print(json.dumps(admission.{function}(Path(sys.argv[1]), "
            "Path(sys.argv[2]))))",
            str(path),
            str(args.kernelbench_root),
        ]
        env = dict(os.environ)
        if check == "interp":
            env["TRITON_INTERPRET"] = "1"
        else:
            env.pop("TRITON_INTERPRET", None)
            env["TRITON_CACHE_DIR"] = str(Path(tempfile.gettempdir()) / f"triton-{path.name}")
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, env=env, timeout=args.timeout, check=False
            )
        except subprocess.TimeoutExpired:
            return {
                "substrate_id": path.name,
                "check": check,
                "verdict": "timeout",
                "seconds": args.timeout,
            }
        lines = completed.stdout.strip().splitlines()
        if completed.returncode == 0 and lines:
            return json.loads(lines[-1])
        return {
            "substrate_id": path.name,
            "check": check,
            "verdict": "crash",
            "stderr_tail": completed.stderr[-1500:],
        }

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for row in pool.map(run, _substrate_dirs(root, args.only)):
            rows.append(row)
            print(
                json.dumps(
                    {k: row.get(k) for k in ("substrate_id", "verdict", "reason")}, sort_keys=True
                ),
                flush=True,
            )
    _write_json(root / f"check_{check.replace('-', '_')}.json", {"rows": rows})
    summary: dict[str, int] = {}
    for row in rows:
        summary[row["verdict"]] = summary.get(row["verdict"], 0) + 1
    print(json.dumps({"summary": summary}, sort_keys=True))
    return 0


def cmd_check_compile(args: argparse.Namespace) -> int:
    return _run_cpu_check(args, "compile")


def cmd_check_interp(args: argparse.Namespace) -> int:
    return _run_cpu_check(args, "interp")


def cmd_check_compile_native(args: argparse.Namespace) -> int:
    return _run_cpu_check(args, "compile-native")


def cmd_admit_gpu(args: argparse.Namespace) -> int:
    return admission.admit_gpu_main(
        Path(args.root), Path(args.kernelbench_root), Path(args.out), only=args.only, seed=args.seed
    )


def cmd_admission_job(args: argparse.Namespace) -> int:
    """One-GPU Slurm job: canonical S1 codegen on the device, S2 build, CPU checks, admission.

    Every step writes under ``--out`` (the job's /outputs), including the Triton and
    Inductor caches. Seed 42 is fixed for admission (hook visibility is structural);
    the job declares the deterministic randomness contract.
    """
    import glob

    if not glob.glob("/dev/nvidia[0-9]*"):
        print(
            "admission-job needs a GPU; run it through the one-GPU Slurm manifest", file=sys.stderr
        )
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TRITON_CACHE_DIR", str(out / ".triton-cache"))
    os.environ.setdefault("TORCHINDUCTOR_CACHE_DIR", str(out / ".inductor-cache"))
    kb = str(args.kernelbench_root)
    records = out / "records-cuda"
    root = out / "substrates"
    steps = [
        [
            "s1-codegen",
            "--kernelbench-root",
            kb,
            "--records-dir",
            str(records),
            "--mode",
            "cuda",
            "--jobs",
            str(args.jobs),
        ],
        ["s1-convert", "--records-dir", str(records), "--out-root", str(root)],
        ["s2-build", "--kernelbench-root", kb, "--out-root", str(root)],
        ["check-static", "--root", str(root)],
        ["split", "--kernelbench-root", kb, "--out", str(root / "split.json")],
        [
            "admit-gpu",
            "--root",
            str(root),
            "--kernelbench-root",
            kb,
            "--out",
            str(root / "admission_hook.jsonl"),
        ],
        [
            "manifest",
            "--root",
            str(root),
            "--split",
            str(root / "split.json"),
            "--out",
            str(out / "corpus_manifest.json"),
        ],
    ]
    for step in steps:
        print(json.dumps({"step": step[0]}), flush=True)
        code = main(step)
        print(json.dumps({"step": step[0], "exit": code}), flush=True)
        # s2-build exits 1 when some entry fails to build; that is logged, not fatal.
        if code != 0 and not (step[0] == "s2-build" and code == 1):
            return code
    return 0


def cmd_parity(args: argparse.Namespace) -> int:
    rows = admission.codegen_parity(Path(args.mock_records), Path(args.cuda_records))
    _write_json(Path(args.out), {"rows": rows})
    summary: dict[str, int] = {}
    for row in rows:
        summary[row["parity"]] = summary.get(row["parity"], 0) + 1
    print(json.dumps({"summary": summary}, sort_keys=True))
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    problems = [pid for pid, _ in kernelbench_problems(Path(args.kernelbench_root), LEVELS)]
    result = split.calibration_split(problems, seed=args.seed)
    _write_json(Path(args.out), result)
    print(
        json.dumps(
            {k: len(v) if isinstance(v, list) else v for k, v in result.items()}, sort_keys=True
        )
    )
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    manifest = admission.corpus_manifest(
        Path(args.root), split_path=Path(args.split) if args.split else None
    )
    _write_json(Path(args.out), manifest)
    print(json.dumps(manifest["summary"], indent=1, sort_keys=True))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    one = sub.add_parser("s1-codegen-one", help=argparse.SUPPRESS)
    one.add_argument("--problem-path", required=True)
    one.add_argument("--problem-id", required=True)
    one.add_argument("--out", required=True)
    one.add_argument("--mode", choices=("mock-h100", "cuda"), default="mock-h100")
    one.add_argument("--gemm-templates", action="store_true")
    one.set_defaults(func=cmd_s1_codegen_one)

    codegen = sub.add_parser("s1-codegen")
    codegen.add_argument("--kernelbench-root", required=True)
    codegen.add_argument("--records-dir", required=True)
    codegen.add_argument("--levels", type=int, nargs="+", default=list(LEVELS))
    codegen.add_argument("--problems", nargs="*")
    codegen.add_argument("--mode", choices=("mock-h100", "cuda"), default="mock-h100")
    codegen.add_argument("--jobs", type=int, default=8)
    codegen.add_argument("--timeout", type=int, default=1200)
    codegen.add_argument("--force", action="store_true")
    codegen.set_defaults(func=cmd_s1_codegen)

    convert = sub.add_parser("s1-convert")
    convert.add_argument("--records-dir", required=True)
    convert.add_argument("--out-root", required=True)
    convert.add_argument("--force", action="store_true")
    convert.set_defaults(func=cmd_s1_convert)

    s2 = sub.add_parser("s2-build")
    s2.add_argument(
        "--sources-root",
        default=str(VENDORED_SOURCES_ROOT),
        help="directory holding FlagGems/, Liger-Kernel/ and triton-tutorials/ "
        "(default: the vendored pinned copies)",
    )
    s2.add_argument("--kernelbench-root", required=True)
    s2.add_argument("--out-root", required=True)
    s2.add_argument("--force", action="store_true")
    s2.set_defaults(func=cmd_s2_build)

    static = sub.add_parser("check-static")
    static.add_argument("--root", required=True)
    static.add_argument("--only", nargs="*")
    static.set_defaults(func=cmd_check_static)

    for name, func in (
        ("check-compile", cmd_check_compile),
        ("check-compile-native", cmd_check_compile_native),
        ("check-interp", cmd_check_interp),
    ):
        check = sub.add_parser(name)
        check.add_argument("--root", required=True)
        check.add_argument("--kernelbench-root", required=True)
        check.add_argument("--only", nargs="*")
        check.add_argument("--jobs", type=int, default=8)
        check.add_argument("--timeout", type=int, default=1800)
        check.set_defaults(func=func)

    gpu = sub.add_parser("admit-gpu")
    gpu.add_argument("--root", required=True)
    gpu.add_argument("--kernelbench-root", required=True)
    gpu.add_argument("--out", required=True)
    gpu.add_argument("--only", nargs="*")
    gpu.add_argument("--seed", type=int, default=42)
    gpu.set_defaults(func=cmd_admit_gpu)

    sp = sub.add_parser("split")
    sp.add_argument("--kernelbench-root", required=True)
    sp.add_argument("--seed", type=int, default=42)
    sp.add_argument("--out", required=True)
    sp.set_defaults(func=cmd_split)

    job = sub.add_parser("admission-job")
    job.add_argument("--kernelbench-root", default=str(DEFAULT_KERNELBENCH_ROOT))
    job.add_argument("--out", required=True)
    job.add_argument("--jobs", type=int, default=8)
    job.set_defaults(func=cmd_admission_job)

    parity = sub.add_parser("parity")
    parity.add_argument("--mock-records", required=True)
    parity.add_argument("--cuda-records", required=True)
    parity.add_argument("--out", required=True)
    parity.set_defaults(func=cmd_parity)

    man = sub.add_parser("manifest")
    man.add_argument("--root", required=True)
    man.add_argument("--split")
    man.add_argument("--out", required=True)
    man.set_defaults(func=cmd_manifest)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
