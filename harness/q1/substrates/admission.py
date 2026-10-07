"""Admission checks for Q1 substrates.

A substrate enters the Stage 0 corpus only if gate (b)'s launch hook can see
its kernels. Four checks, cheapest first:

``static_check`` (pure Python)
    ``kernel.py`` defines ``ModelNew`` with ``forward``; every Triton launch is a
    plain ``kernel[grid](...)`` on a module-level ``@triton.jit`` function (optionally
    under ``@triton.autotune``/``@triton.heuristics``); nothing references
    ``libentry``, ``triton_heuristics``, ``CachingAutotuner`` or a static launcher.
    Patterns that KernelBench's static checker treats as strict (``try``/``except``,
    ``pass``) are reported as warnings, because gate ``a_static`` would reject them.

``compile_check`` (torch + triton, no GPU)
    Runs ``ModelNew.forward`` on small CPU inputs with every JIT launch turned into
    a compile-only warmup for ``GPUTarget("cuda", 90, 32)``; each autotuned kernel
    is compiled for every config. Records register and shared-memory use from the
    bundled ``cuobjdump``. Proves the kernels compile for an H100 and that every
    launch goes through ``JITFunction.run``.

``interpreter_check`` (torch + triton with ``TRITON_INTERPRET=1``, no GPU)
    Runs ``ModelNew`` and the reference ``Model`` on small CPU inputs and compares
    them. This validates the conversion (argument order, grids, guards); it is
    build validation, not correctness evidence, and its tolerance is loose.

``admit_gpu_main`` (one GPU, inside a Slurm job only)
    At native shapes with seed 42, gate (b)'s own ``LaunchHook``
    (``harness.q1.gates.gate_b``, falling back to :class:`LaunchRecorder` on
    ``JITFunction.run`` and ``Autotuner.run`` when the core package is absent)
    must observe at least one launch under ``torch.inference_mode()`` and under
    ``torch.enable_grad()``, after one unhooked warmup call as in b1. Writes
    ``admission_hook`` verdict rows.

Small inputs come from the problem's own ``get_inputs`` after shrinking its
module-level integer sizes that ``get_init_inputs`` does not use (parameters are
static in the compiled graph), so the inputs keep the problem's distributions.
"""

from __future__ import annotations

import ast
import contextlib
import importlib.util
import json
import math
import re
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

from harness.q1.schema import (
    SchemaError,
    load_kernel_dir,
    make_verdict_row,
    sha256_file,
)
from harness.q1.substrates.sources import problem_file

ADMISSION_VERSION = "q1-substrate-admission/1"

FORBIDDEN_NAMES = {
    "libentry",
    "LibEntry",
    "triton_heuristics",
    "CachingAutotuner",
    "cached_autotune",
    "StaticallyLaunchedCudaKernel",
    "static_launcher",
    "set_driver_to_gpu",
}
#: Regexes KernelBench@423217d9's kernel_static_checker treats as strict (code_bypass).
STRICT_STATIC_PATTERNS = {
    "try": r"\btry\s*:",
    "except": r"\bexcept\s*:|\bexcept\s+\w+",
    "pass": r"\bpass\b",
}
#: Small-input budget for CPU checks: largest tensor and total elements.
MAX_TENSOR_NUMEL = 1 << 18
MAX_TOTAL_NUMEL = 1 << 20
INTERP_ATOL = 1e-3
INTERP_RTOL = 1e-3


# --- static check ----------------------------------------------------------------


def _decorator_names(function: ast.FunctionDef) -> list[str]:
    names = []
    for decorator in function.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        names.append(ast.unparse(target))
    return names


def jit_functions(tree: ast.Module) -> dict[str, dict[str, Any]]:
    """Module-level functions compiled by Triton, with their decorator stack."""
    found: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        names = _decorator_names(node)
        if not names or names[-1] not in ("triton.jit", "jit"):
            continue
        outer = names[:-1]
        allowed = {"triton.autotune", "autotune", "triton.heuristics", "heuristics"}
        found[node.name] = {
            "decorators": names,
            "autotuned": any(name in ("triton.autotune", "autotune") for name in outer),
            "unexpected_decorators": [name for name in outer if name not in allowed],
            "line": node.lineno,
        }
    return found


def launch_sites(tree: ast.Module, kernels: set[str]) -> list[dict[str, Any]]:
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Subscript) and isinstance(func.value, ast.Name):
            if func.value.id in kernels:
                sites.append({"kernel": func.value.id, "kind": "subscript", "line": node.lineno})
        elif (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in kernels
            and func.attr in ("run", "warmup", "__getitem__")
        ):
            sites.append({"kernel": func.value.id, "kind": func.attr, "line": node.lineno})
    return sorted(sites, key=lambda site: site["line"])


def static_check(path: Path) -> dict[str, Any]:
    """Pure-Python launch-path admission for one substrate directory."""
    path = Path(path)
    row: dict[str, Any] = {
        "substrate_id": path.name,
        "check": "static",
        "admission_version": ADMISSION_VERSION,
    }
    reasons: list[str] = []
    try:
        kernel_dir = load_kernel_dir(path)
    except SchemaError as exc:
        return {**row, "verdict": "fail", "reasons": [f"schema: {exc}"]}
    if kernel_dir.kind != "substrate":
        reasons.append(f"not a substrate directory ({kernel_dir.kind})")
    source = (path / "kernel.py").read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {**row, "verdict": "fail", "reasons": [f"syntax: {exc}"]}
    model_new = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ModelNew"]
    if len(model_new) != 1:
        reasons.append("kernel.py must define exactly one module-level class ModelNew")
    elif not any(
        isinstance(item, ast.FunctionDef) and item.name == "forward" for item in model_new[0].body
    ):
        reasons.append("ModelNew has no forward")
    kernels = jit_functions(tree)
    if not kernels:
        reasons.append("no module-level @triton.jit function")
    for name, info in kernels.items():
        if info["unexpected_decorators"]:
            reasons.append(f"{name}: unexpected decorators {info['unexpected_decorators']}")
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
        elif isinstance(node, ast.alias):
            used.add((node.asname or node.name).split(".")[-1])
            used.add(node.name.split(".")[-1])
    forbidden = sorted(used & FORBIDDEN_NAMES)
    if forbidden:
        reasons.append(f"forbidden launch-path names: {forbidden}")
    sites = launch_sites(tree, set(kernels))
    direct = [site for site in sites if site["kind"] != "subscript"]
    if direct:
        reasons.append(f"direct .run/.warmup launches: {direct}")
    if not any(site["kind"] == "subscript" for site in sites):
        reasons.append("no kernel[grid](...) launch site")
    launched = {site["kernel"] for site in sites}
    called_helpers = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in kernels:
            called_helpers |= {
                n.func.id
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and (node.func.attr == "associative_scan")
        ):
            called_helpers |= {a.id for a in node.args if isinstance(a, ast.Name)}
    never_launched = sorted(set(kernels) - launched - called_helpers)
    stripped = re.sub(r"(?m)#.*$", "", source)
    warnings = [
        name for name, pattern in STRICT_STATIC_PATTERNS.items() if re.search(pattern, stripped)
    ]
    return {
        **row,
        "verdict": "pass" if not reasons else "fail",
        "reasons": reasons,
        "jit_kernels": sorted(kernels),
        "autotuned_kernels": sorted(name for name, info in kernels.items() if info["autotuned"]),
        "launch_sites": len(sites),
        "launched_kernels": sorted(launched),
        "unlaunched_jit_functions": never_launched,
        "kernelbench_strict_static_warnings": warnings,
        "kernel_sha256": sha256_file(path / "kernel.py"),
    }


# --- small inputs ----------------------------------------------------------------


def _int_value(node: ast.expr, env: dict[str, int]) -> int | None:
    """Evaluate a literal integer expression (ints, + - * // **, known names)."""
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    ):
        return node.value
    if isinstance(node, ast.Name) and node.id in env:
        return env[node.id]
    if isinstance(node, ast.BinOp) and isinstance(
        node.op, ast.Add | ast.Sub | ast.Mult | ast.FloorDiv | ast.Pow
    ):
        left, right = _int_value(node.left, env), _int_value(node.right, env)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.FloorDiv):
            return left // right if right else None
        return left**right if 0 <= right < 64 else None
    return None


def _assignment_pairs(node: ast.stmt) -> list[tuple[str, ast.expr]]:
    """``(name, value)`` pairs of a module-level assignment: ``a = 1``, ``a = b = 1``,
    ``a, b = 1, 2``. Anything else yields no pairs."""
    if not isinstance(node, ast.Assign):
        return []
    pairs: list[tuple[str, ast.expr]] = []
    for target in node.targets:
        if isinstance(target, ast.Name):
            pairs.append((target.id, node.value))
        elif (
            isinstance(target, ast.Tuple)
            and isinstance(node.value, ast.Tuple)
            and len(target.elts) == len(node.value.elts)
            and all(isinstance(elt, ast.Name) for elt in target.elts)
        ):
            pairs.extend(
                (elt.id, value) for elt, value in zip(target.elts, node.value.elts, strict=True)
            )
        else:
            return []
    return pairs


def shrinkable_sizes(problem_source: str) -> tuple[dict[str, int], set[str]]:
    """Module-level integer sizes and the subset frozen by ``get_init_inputs`` or ``Model``."""
    tree = ast.parse(problem_source)
    sizes: dict[str, int] = {}
    deps: dict[str, set[str]] = {}
    init_names: set[str] = set()
    for node in tree.body:
        for name, value_node in _assignment_pairs(node):
            deps[name] = {n.id for n in ast.walk(value_node) if isinstance(n, ast.Name)}
            value = _int_value(value_node, sizes)
            if value is not None:
                sizes[name] = value
        if isinstance(node, ast.FunctionDef) and node.name == "get_init_inputs":
            init_names |= {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        if isinstance(node, ast.ClassDef) and node.name == "Model":
            # Constants read as globals inside the model are part of the compiled program.
            init_names |= {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    frozen: set[str] = set()
    stack = list(init_names)
    while stack:
        name = stack.pop()
        if name in frozen:
            continue
        frozen.add(name)
        stack.extend(deps.get(name, ()))
    return sizes, frozen


def shrunk_source(problem_source: str, overrides: dict[str, int]) -> str:
    """Rewrite module-level size assignments, splitting chained and tuple forms."""
    tree = ast.parse(problem_source)
    body: list[ast.stmt] = []
    for node in tree.body:
        pairs = _assignment_pairs(node)
        if pairs and any(name in overrides for name, _ in pairs):
            for name, value_node in pairs:
                value = ast.Constant(overrides[name]) if name in overrides else value_node
                body.append(
                    ast.Assign(
                        targets=[ast.Name(name, ast.Store())], value=value, lineno=node.lineno
                    )
                )
        else:
            body.append(node)
    tree.body = body
    return ast.unparse(ast.fix_missing_locations(tree))


def _exec_problem(source: str, name: str = "q1_problem") -> Any:
    import types

    module = types.ModuleType(name)
    exec(compile(source, f"<{name}>", "exec"), module.__dict__)  # noqa: S102 - trusted problem file
    return module


def _evaluate_shrink(problem_source: str, override: dict[str, int], guard_check) -> dict:
    """Meta-device inputs for ``override`` and why they are unusable (``problem``), if so."""
    import torch

    try:
        module = _exec_problem(shrunk_source(problem_source, override))
        with torch.device("meta"):
            inputs = list(module.get_inputs())
    except Exception as exc:  # noqa: BLE001 - this shrink is unusable
        return {"problem": f"{type(exc).__name__}: {exc}"[:200], "numel": None}
    numels = [t.numel() for t in inputs if isinstance(t, torch.Tensor)]
    if not numels:
        return {"problem": "no tensor inputs", "numel": None}
    if guard_check is not None:
        problem = guard_check(inputs)
        if problem:
            return {"problem": f"guard: {problem}", "numel": sum(numels)}
    return {
        "problem": None,
        "numel": sum(numels),
        "max_numel": max(numels),
        "shapes": [list(t.shape) if isinstance(t, torch.Tensor) else repr(t) for t in inputs],
    }


def choose_small_inputs(problem_source: str, guard_check=None) -> dict[str, Any]:
    """Shrink the problem's free sizes greedily until the inputs fit the CPU budget.

    Starting from the native sizes, repeatedly halve (never below 2) the largest
    free size whose halving keeps ``get_inputs`` valid and the substrate's guards
    satisfied. Deterministic: ties break by name.
    """
    sizes, frozen = shrinkable_sizes(problem_source)
    current = {name: value for name, value in sizes.items() if name not in frozen and value >= 2}
    state = _evaluate_shrink(problem_source, current, guard_check)
    if state["problem"] is not None:
        return {"override": None, "tried": [{"override": current, **state}]}
    tried: list[dict[str, Any]] = []

    def fits(result: dict) -> bool:
        return result["max_numel"] <= MAX_TENSOR_NUMEL and result["numel"] <= MAX_TOTAL_NUMEL

    while not fits(state):
        progressed = False
        for name in sorted(current, key=lambda n: (-current[n], n)):
            if current[name] <= 2:
                continue
            trial = {**current, name: max(2, current[name] // 2)}
            result = _evaluate_shrink(problem_source, trial, guard_check)
            if result["problem"] is None:
                current, state, progressed = trial, result, True
                break
            tried.append({"override": trial, "problem": result["problem"]})
        if not progressed:
            return {"override": None, "tried": tried[-3:], "last": current}
    return {
        "override": current,
        "source": shrunk_source(problem_source, current),
        "shapes": state["shapes"],
    }


# --- CPU execution harness ----------------------------------------------------------


def load_kernel_module(path: Path, name: str = "q1_substrate_kernel") -> Any:
    spec = importlib.util.spec_from_file_location(name, str(path / "kernel.py"))
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def cpu_device_shims(kernel_module: Any, device: str = "cpu"):
    """Let a CUDA-targeting substrate run its host code on CPU (or meta) tensors."""
    import torch

    saved = {
        "_DeviceGuard": torch.cuda._DeviceGuard,
        "set_device": torch.cuda.set_device,
        "device": torch.cuda.device,
    }

    class _NoGuard:
        def __init__(self, *args, **kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    torch.cuda._DeviceGuard = _NoGuard
    torch.cuda.set_device = lambda *args, **kwargs: None
    torch.cuda.device = _NoGuard
    module_saved = {}
    if hasattr(kernel_module, "empty_strided_cuda"):
        module_saved["empty_strided_cuda"] = kernel_module.empty_strided_cuda
        kernel_module.empty_strided_cuda = lambda size, stride, dtype: torch.empty_strided(
            size, stride, dtype=dtype, device=device
        )
    if hasattr(kernel_module, "_check_tensor"):
        module_saved["_check_tensor"] = kernel_module._check_tensor
        refusal = kernel_module.SubstrateRefusal

        def check_tensor_cpu(value, dtype, ndim, source):
            if not isinstance(value, torch.Tensor) or value.dtype != dtype or value.dim() != ndim:
                raise refusal(f"{source}: dtype/rank mismatch")
            return None

        kernel_module._check_tensor = check_tensor_cpu
    try:
        yield
    finally:
        torch.cuda._DeviceGuard = saved["_DeviceGuard"]
        torch.cuda.set_device = saved["set_device"]
        torch.cuda.device = saved["device"]
        for key, value in module_saved.items():
            setattr(kernel_module, key, value)


def _s1_guard_check(path: Path, instance: Any = None):
    """Guard predicate for S1 substrates: evaluate the substrate's own shape guards."""
    build_path = path / "build.json"
    if not build_path.exists():
        return None
    build = json.loads(build_path.read_text(encoding="utf-8"))
    guards = build.get("guards") or {}
    sources = guards.get("symbol_sources", {})
    ranges = guards.get("symbol_ranges", {})
    expressions = guards.get("expressions", [])
    placeholders = build.get("placeholders", [])

    def check(inputs: list[Any]) -> str | None:
        import torch

        names = _forward_arg_names(path)
        local = {**dict(zip(names, inputs, strict=False)), "self": instance}
        scope = {"L": local, "torch": torch, "math": math}
        try:
            values = {sym: eval(src, scope) for sym, src in sources.items()}  # noqa: S307
        except Exception as exc:  # noqa: BLE001
            return f"symbol binding failed: {exc}"
        for sym, (lower, upper) in ranges.items():
            if sym in values and lower is not None and values[sym] < lower:
                return f"{sym}={values[sym]} < {lower}"
            if sym in values and upper is not None and values[sym] > upper:
                return f"{sym}={values[sym]} > {upper}"
        for expression in expressions:
            try:
                ok = eval(expression, {"torch": torch, "math": math}, dict(values))  # noqa: S307
            except Exception as exc:  # noqa: BLE001
                return f"guard {expression} failed to evaluate: {exc}"
            if not ok:
                return f"guard {expression}"
        for placeholder in placeholders:
            if placeholder.get("kind") == "tensor":
                value = eval(placeholder["source"], scope)  # noqa: S307
                if not isinstance(value, torch.Tensor) or value.dim() != placeholder["ndim"]:
                    return f"{placeholder['source']} rank"
        return None

    return check


def _forward_arg_names(path: Path) -> list[str]:
    tree = ast.parse((path / "kernel.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "ModelNew":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "forward":
                    return [arg.arg for arg in item.args.args[1:]]
    # S2 ModelNew may inherit forward signature names from the reference Model
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Model":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "forward":
                    return [arg.arg for arg in item.args.args[1:]]
    return []


def _problem_source(path: Path, kernelbench_root: Path) -> tuple[str, str]:
    substrate = json.loads((path / "substrate.json").read_text(encoding="utf-8"))
    problem_id = substrate["problem_id"]
    source = problem_file(kernelbench_root, problem_id).read_text(encoding="utf-8")
    return problem_id, source


def _compare(reference: Any, candidate: Any) -> dict[str, Any]:
    import torch

    refs = reference if isinstance(reference, tuple | list) else [reference]
    outs = candidate if isinstance(candidate, tuple | list) else [candidate]
    if len(refs) != len(outs):
        return {"match": False, "reason": f"output count {len(outs)} != {len(refs)}"}
    worst_abs = 0.0
    worst_rel = 0.0
    for ref, out in zip(refs, outs, strict=True):
        if not isinstance(out, torch.Tensor) or out.shape != ref.shape:
            return {"match": False, "reason": f"shape {getattr(out, 'shape', None)} != {ref.shape}"}
        if not ref.dtype.is_floating_point:
            if out.dtype != ref.dtype or not torch.equal(out, ref):
                return {"match": False, "reason": "integer output mismatch"}
            continue
        if not torch.equal(torch.isnan(out), torch.isnan(ref)):
            return {"match": False, "reason": "NaN mask mismatch"}
        finite = torch.isfinite(ref) & torch.isfinite(out)
        diff = (out.double() - ref.double()).abs()[finite]
        if diff.numel():
            worst_abs = max(worst_abs, float(diff.max()))
            rel = diff / ref.double().abs()[finite].clamp_min(1e-12)
            worst_rel = max(worst_rel, float(rel.max()))
        if not torch.allclose(out, ref, atol=INTERP_ATOL, rtol=INTERP_RTOL, equal_nan=True):
            return {
                "match": False,
                "reason": "allclose",
                "max_abs_err": worst_abs,
                "max_rel_err": worst_rel,
            }
    return {"match": True, "max_abs_err": worst_abs, "max_rel_err": worst_rel}


def _run_on_cpu(path: Path, kernelbench_root: Path, mode: str) -> dict[str, Any]:
    """Shared body of the CPU checks (one substrate, this process).

    ``compile`` and ``interpret`` use small CPU inputs from :func:`choose_small_inputs`;
    ``compile-native`` uses the problem's native shapes on the meta device (nothing is
    allocated or executed), so shape-dependent block sizes compile as on the GPU.
    """
    import torch

    started = time.monotonic()
    row: dict[str, Any] = {
        "substrate_id": Path(path).name,
        "check": mode,
        "admission_version": ADMISSION_VERSION,
    }
    problem_id, problem_source = _problem_source(path, kernelbench_root)
    kernel_module = load_kernel_module(path)
    native = _exec_problem(problem_source)
    torch.manual_seed(42)
    candidate = kernel_module.ModelNew(*native.get_init_inputs())
    if mode == "compile-native":
        with torch.device("meta"):
            inputs = list(native.get_inputs())
        candidate = candidate.to("meta")
        row["native_shapes"] = [
            list(t.shape) if isinstance(t, torch.Tensor) else repr(t) for t in inputs
        ]
        expected = None
        device = "meta"
    else:
        small = choose_small_inputs(problem_source, _s1_guard_check(path, candidate))
        row["small_inputs"] = {k: small[k] for k in ("override", "shapes") if k in small}
        if small.get("override") is None:
            return {**row, "verdict": "no-small-shape", "tried": small.get("tried")}
        problem = _exec_problem(small["source"])
        torch.manual_seed(42)
        reference = problem.Model(*problem.get_init_inputs())
        torch.manual_seed(42)
        inputs = list(problem.get_inputs())
        with torch.no_grad():
            expected = reference(*[t.clone() if isinstance(t, torch.Tensor) else t for t in inputs])
        device = "cpu"
    refusal = getattr(kernel_module, "SubstrateRefusal", None)
    recorder = _InterpreterLaunches() if mode == "interpret" else _CompileOnly()
    with torch.no_grad():
        try:
            with cpu_device_shims(kernel_module, device), recorder:
                got = candidate(*inputs)
        except Exception as exc:  # noqa: BLE001 - classified into the row
            if refusal is not None and isinstance(exc, refusal):
                return {
                    **row,
                    "verdict": "refuse",
                    "reason": str(exc)[:300],
                    "seconds": round(time.monotonic() - started, 2),
                }
            kind = "unsupported" if isinstance(exc, NotImplementedError) else "error"
            return {
                **row,
                "verdict": kind,
                "reason": f"{type(exc).__name__}: {exc}"[:600],
                "traceback_tail": traceback.format_exc()[-1500:],
                "launches": recorder.summary(),
                "seconds": round(time.monotonic() - started, 2),
            }
    row["launches"] = recorder.summary()
    row["seconds"] = round(time.monotonic() - started, 2)
    if not row["launches"]["count"]:
        return {**row, "verdict": "fail", "reason": "no Triton launch observed"}
    if mode != "interpret":
        return {**row, "verdict": "pass"}
    comparison = _compare(expected, got)
    return {**row, "verdict": "pass" if comparison["match"] else "fail", **comparison}


class _CompileOnly:
    """Turn every JIT launch into a compile-only warmup for sm_90; compile every autotune config."""

    def __init__(self) -> None:
        self.launches: list[dict[str, Any]] = []

    def __enter__(self):
        import torch
        import triton
        from triton.backends.compiler import GPUTarget
        from triton.runtime import autotuner, jit
        from triton.runtime.driver import driver

        class _Driver:
            def get_current_target(self):
                return GPUTarget("cuda", 90, 32)

            def get_active_torch_device(self):
                return torch.device("cpu")

            def get_current_device(self):
                return 0

            def get_current_stream(self, device=None):
                return 0

            def get_device_interface(self):
                return torch.cuda

            def is_active(self):
                return True

        # Never touch driver.active here: resolving it would try to load libcuda.
        driver.set_active(_Driver())
        self._jit_run = jit.JITFunction.run
        self._autotune_run = autotuner.Autotuner.run
        recorder = self

        def jit_run(fn_self, *args, grid, warmup, **kwargs):
            kernel = recorder._jit_run(fn_self, *args, grid=grid, warmup=True, **kwargs)
            recorder.launches.append(_compiled_info(fn_self, kernel, kwargs))
            return kernel

        def autotune_run(tuner, *args, **kwargs):
            for config in tuner.configs:
                merged = {**kwargs, **config.all_kwargs()}
                tuner.fn.run(*args, **merged)
            return None

        jit.JITFunction.run = jit_run
        autotuner.Autotuner.run = autotune_run
        self._triton = triton
        return self

    def __exit__(self, *exc):
        from triton.runtime import autotuner, jit
        from triton.runtime.driver import driver

        jit.JITFunction.run = self._jit_run
        autotuner.Autotuner.run = self._autotune_run
        # reset_active() would build the default (CUDA) driver; restore the lazy state.
        driver._active = None
        return False

    def summary(self) -> dict[str, Any]:
        return {"count": len(self.launches), "kernels": self.launches}


def _compiled_info(fn: Any, kernel: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    info: dict[str, Any] = {
        "kernel": getattr(fn, "__name__", repr(fn)),
        "num_warps": kwargs.get("num_warps"),
        "num_stages": kwargs.get("num_stages"),
    }
    metadata = getattr(kernel, "metadata", None)
    if metadata is not None:
        info["shared_bytes"] = getattr(metadata, "shared", None)
        info["target"] = str(getattr(metadata, "target", ""))
    cubin = getattr(kernel, "asm", {}).get("cubin") if kernel is not None else None
    if cubin:
        info.update(_cuobjdump_usage(cubin))
    return info


def _cuobjdump_usage(cubin: bytes) -> dict[str, Any]:
    """Register, stack, shared and local use from Triton's bundled cuobjdump."""
    try:
        import triton.backends.nvidia as nvidia

        tool = Path(nvidia.__file__).parent / "bin" / "cuobjdump"
        with tempfile.NamedTemporaryFile(suffix=".cubin") as handle:
            handle.write(cubin)
            handle.flush()
            completed = subprocess.run(
                [str(tool), "--dump-resource-usage", handle.name],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        usage = {}
        for key in ("REG", "STACK", "SHARED", "LOCAL"):
            match = re.search(rf"{key}:(\d+)", completed.stdout)
            if match:
                usage[key.lower()] = int(match.group(1))
        return usage
    except (OSError, subprocess.SubprocessError) as exc:
        return {"cuobjdump_error": str(exc)[:200]}


#: libdevice functions evaluated with NumPy under the interpreter (which cannot run
#: extern calls). float32 NumPy math; only the conversion check uses these.
_LIBDEVICE_NUMPY = {
    "exp": "exp",
    "exp2": "exp2",
    "expm1": "expm1",
    "log": "log",
    "log2": "log2",
    "log10": "log10",
    "log1p": "log1p",
    "sqrt": "sqrt",
    "tanh": "tanh",
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "sinh": "sinh",
    "cosh": "cosh",
    "atan": "arctan",
    "asin": "arcsin",
    "acos": "arccos",
    "floor": "floor",
    "ceil": "ceil",
    "trunc": "trunc",
    "nearbyint": "rint",
    "rint": "rint",
    "fabs": "abs",
    "abs": "abs",
    "isnan": "isnan",
    "isinf": "isinf",
    "signbit": "signbit",
    "pow": "power",
    "fmod": "fmod",
    "atan2": "arctan2",
    "fmax": "fmax",
    "fmin": "fmin",
    "copysign": "copysign",
}


def _libdevice_numpy_shims() -> dict[str, Any]:
    import numpy as np
    import triton.language as tl
    from triton.runtime.interpreter import TensorHandle

    def special_erf(data):
        try:
            from scipy.special import erf
        except ImportError:  # pragma: no cover - scipy is in the image
            return np.vectorize(math.erf, otypes=[data.dtype])(data)
        return erf(data)

    def make(np_fn):
        def shim(*args, _semantic=None, **kwargs):
            ref = next(a for a in args if isinstance(a, tl.tensor))
            datas = [a.handle.data if isinstance(a, tl.tensor) else np.asarray(a) for a in args]
            out = np.asarray(np_fn(*datas))
            if out.dtype == np.bool_:
                dtype = tl.int1
            else:
                dtype = ref.dtype.scalar if hasattr(ref.dtype, "scalar") else ref.dtype
                out = out.astype(ref.handle.data.dtype)
            ty = tl.block_type(dtype, ref.type.shape) if ref.type.is_block() else dtype
            return tl.tensor(TensorHandle(out, dtype), ty)

        return shim

    shims = {name: make(getattr(np, np_name)) for name, np_name in _LIBDEVICE_NUMPY.items()}
    shims["erf"] = make(special_erf)
    shims["rsqrt"] = make(lambda data: 1.0 / np.sqrt(data))
    return shims


class _InterpreterLaunches:
    """Count launches under TRITON_INTERPRET=1; pin autotuned kernels to their first config.

    Also binds grid callables as compiled JIT does, works around Triton 3.6's
    interpreter calling ``int()`` on 1-element arrays (rejected by NumPy 2.5), and
    evaluates libdevice calls with NumPy, since the interpreter cannot run extern
    calls. All three are shims of the check, not of the substrate.
    """

    def __init__(self) -> None:
        self.launches: list[str] = []

    def __enter__(self):
        import os

        from triton.runtime import autotuner, interpreter

        if os.environ.get("TRITON_INTERPRET") != "1":
            raise RuntimeError("interpreter check needs TRITON_INTERPRET=1 before triton import")
        self._run = interpreter.InterpretedFunction.run
        self._autotune_run = autotuner.Autotuner.run
        recorder = self

        def run(fn_self, *args, grid, warmup, **kwargs):
            recorder.launches.append(getattr(fn_self, "__name__", repr(fn_self)))
            if callable(grid):
                # The compiled JIT path hands grid callables Python values; the
                # interpreter would hand them interpreter tensors. Bind as JIT does.
                meta = {**dict(zip(fn_self.arg_names, args, strict=False)), **kwargs}
                grid = grid(meta)
            return recorder._run(fn_self, *args, grid=grid, warmup=warmup, **kwargs)

        def autotune_run(tuner, *args, **kwargs):
            config = tuner.configs[0]
            return tuner.fn.run(*args, **{**kwargs, **config.all_kwargs()})

        interpreter.InterpretedFunction.run = run
        autotuner.Autotuner.run = autotune_run
        # Triton 3.6's interpreter converts 1-element arrays with int(), which
        # NumPy 2.5 rejects; index through the single element instead.
        self._patch_lang_tensor = interpreter._patch_lang_tensor

        def patch_lang_tensor(tensor, scope):
            self._patch_lang_tensor(tensor, scope)
            scope.set_attr(tensor, "__index__", lambda value: int(value.handle.data.reshape(-1)[0]))

        interpreter._patch_lang_tensor = patch_lang_tensor
        from triton.language.extra import libdevice

        self._libdevice = libdevice
        self._libdevice_saved = {
            name: getattr(libdevice, name) for name in dir(libdevice) if not name.startswith("_")
        }
        for name, shim in _libdevice_numpy_shims().items():
            setattr(libdevice, name, shim)
        return self

    def __exit__(self, *exc):
        from triton.runtime import autotuner, interpreter

        interpreter.InterpretedFunction.run = self._run
        autotuner.Autotuner.run = self._autotune_run
        interpreter._patch_lang_tensor = self._patch_lang_tensor
        for name, value in self._libdevice_saved.items():
            setattr(self._libdevice, name, value)
        return False

    def summary(self) -> dict[str, Any]:
        return {"count": len(self.launches), "kernels": sorted(set(self.launches))}


def compile_check(path: Path, kernelbench_root: Path) -> dict[str, Any]:
    return _run_on_cpu(Path(path), Path(kernelbench_root), "compile")


def native_compile_check(path: Path, kernelbench_root: Path) -> dict[str, Any]:
    return _run_on_cpu(Path(path), Path(kernelbench_root), "compile-native")


def interpreter_check(path: Path, kernelbench_root: Path) -> dict[str, Any]:
    return _run_on_cpu(Path(path), Path(kernelbench_root), "interpret")


# --- GPU admission (Slurm job only) -----------------------------------------------


class LaunchRecorder:
    """Record Triton launches through the classes KernelGYM's detector patches.

    Patches ``triton.runtime.jit.JITFunction.run`` (reached by ``kernel[grid](...)``
    through ``KernelInterface.__getitem__``) and ``triton.runtime.autotuner.Autotuner.run``.
    The core owner's gate (b) hook can replace this via ``hook_factory``.
    """

    def __init__(self) -> None:
        self.launches: list[str] = []

    def __enter__(self):
        from triton.runtime import autotuner, jit

        self._jit_run = jit.JITFunction.run
        self._autotune_run = autotuner.Autotuner.run
        recorder = self

        def jit_run(fn_self, *args, **kwargs):
            if not kwargs.get("warmup", False):
                recorder.launches.append(getattr(fn_self, "__name__", "jit"))
            return recorder._jit_run(fn_self, *args, **kwargs)

        def autotune_run(tuner, *args, **kwargs):
            recorder.launches.append(f"autotune:{getattr(tuner.fn, '__name__', 'fn')}")
            return recorder._autotune_run(tuner, *args, **kwargs)

        jit.JITFunction.run = jit_run
        autotuner.Autotuner.run = autotune_run
        return self

    def __exit__(self, *exc):
        from triton.runtime import autotuner, jit

        jit.JITFunction.run = self._jit_run
        autotuner.Autotuner.run = self._autotune_run
        return False


def default_hook_factory():
    """Gate (b)'s own launch hook when the core package is present, else :class:`LaunchRecorder`."""
    try:
        from harness.q1.gates.gate_b import LaunchHook  # core owner's b1 hook
    except ImportError:
        return LaunchRecorder, "harness.q1.substrates.admission.LaunchRecorder"
    return LaunchHook, "harness.q1.gates.gate_b.LaunchHook"


def _captured(hook: Any) -> list[str]:
    return list(getattr(hook, "captured", None) or getattr(hook, "launches", None) or [])


def admit_one_gpu(
    path: Path, kernelbench_root: Path, seed: int = 42, hook_factory=None
) -> list[dict[str, Any]]:
    """Hook-visibility admission at native shapes on the current CUDA device.

    Mirrors b1's protocol: per grad mode, one unhooked warmup call, then one call
    under the hook; the mode is accepted when the hook records a launch. An
    exception is ``refuse`` for :class:`SubstrateRefusal` and ``error`` otherwise.
    """
    import torch

    path = Path(path)
    substrate_id = path.name
    if hook_factory is None:
        hook_factory, hook_name = default_hook_factory()
    else:
        hook_name = getattr(hook_factory, "__qualname__", repr(hook_factory))
    problem_id, problem_source = _problem_source(path, kernelbench_root)
    problem = _exec_problem(problem_source)
    kernel_module = load_kernel_module(path)
    device = torch.device("cuda", torch.cuda.current_device())
    refusal = getattr(kernel_module, "SubstrateRefusal", None)
    rows = []
    torch.manual_seed(seed)
    model_new = kernel_module.ModelNew(*problem.get_init_inputs()).to(device)
    # Hook visibility does not depend on input values, so inputs are drawn directly on
    # the device (seeded CUDA generator) instead of KernelBench's CPU draw and copy.
    torch.manual_seed(seed)
    with torch.device(device):
        inputs = list(problem.get_inputs())
    inputs = [t.to(device) if isinstance(t, torch.Tensor) else t for t in inputs]
    for grad_mode, context in (
        ("inference_mode", torch.inference_mode),
        ("enable_grad", torch.enable_grad),
    ):
        started = time.monotonic()
        start_event = torch.cuda.Event(enable_timing=True)
        end_event = torch.cuda.Event(enable_timing=True)
        details: dict[str, Any] = {
            "admission_version": ADMISSION_VERSION,
            "grad_mode": grad_mode,
            "problem_id": problem_id,
            "hook": hook_name,
            "protocol": "warmup 1 unhooked, step 1 hooked",
            "kernel_sha256": sha256_file(path / "kernel.py"),
        }
        try:
            start_event.record()
            with context():
                model_new(*inputs)
            torch.cuda.synchronize()
            hook = hook_factory()
            with context(), hook:
                model_new(*inputs)
                torch.cuda.synchronize()
            end_event.record()
            torch.cuda.synchronize()
            captured = _captured(hook)
            details["launches"] = len(captured)
            details["kernels_seen"] = sorted(set(captured))[:50]
            verdict = "accept" if captured else "reject"
            gpu_seconds = start_event.elapsed_time(end_event) / 1000.0
        except Exception as exc:  # noqa: BLE001 - classified into the row
            torch.cuda.synchronize()
            is_refusal = refusal is not None and isinstance(exc, refusal)
            verdict = "refuse" if is_refusal else "error"
            details["exception"] = f"{type(exc).__name__}: {exc}"[:800]
            gpu_seconds = 0.0
        rows.append(
            make_verdict_row(
                kernel_id=substrate_id,
                gate="admission_hook",
                config_id=f"native-seed{seed}-{grad_mode}",
                verdict=verdict,
                tf32_policy="torch-default",
                gpu_seconds=gpu_seconds,
                wall_seconds=time.monotonic() - started,
                details=details,
                seed=seed,
            )
        )
    return rows


def admit_gpu_main(
    root: Path,
    kernelbench_root: Path,
    out: Path,
    *,
    only: list[str] | None,
    seed: int = 42,
    timeout: int = 900,
) -> int:
    """Run :func:`admit_one_gpu` per substrate in its own process; append rows to ``out``."""
    import glob

    if not glob.glob("/dev/nvidia[0-9]*"):
        print("admit-gpu needs a GPU; run it inside the one-GPU Slurm job", file=sys.stderr)
        return 2
    root = Path(root)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                done.add((row["kernel_id"], row["config_id"]))
    dirs = sorted(p for p in root.iterdir() if (p / "substrate.json").exists())
    if only:
        dirs = [p for p in dirs if p.name in set(only)]
    project_root = Path(__file__).resolve().parents[3]
    for path in dirs:
        configs = {f"native-seed{seed}-{mode}" for mode in ("inference_mode", "enable_grad")}
        if all((path.name, config) in done for config in configs):
            continue
        command = [
            sys.executable,
            "-c",
            "import json, sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(project_root)!r}); "
            "from harness.q1.substrates.admission import admit_one_gpu; "
            "print(json.dumps(admit_one_gpu(Path(sys.argv[1]), Path(sys.argv[2]), "
            "int(sys.argv[3]))))",
            str(path),
            str(kernelbench_root),
            str(seed),
        ]
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, check=False
            )
            lines = completed.stdout.strip().splitlines()
            rows = json.loads(lines[-1]) if completed.returncode == 0 and lines else None
            failure = None if rows else f"exit {completed.returncode}: {completed.stderr[-600:]}"
            verdict = "error"
        except subprocess.TimeoutExpired:
            rows, failure, verdict = None, f"timeout after {timeout}s", "timeout"
        if rows is None:
            rows = [
                make_verdict_row(
                    kernel_id=path.name,
                    gate="admission_hook",
                    config_id=config,
                    verdict=verdict,
                    tf32_policy="torch-default",
                    wall_seconds=time.monotonic() - started,
                    details={"admission_version": ADMISSION_VERSION, "failure": failure},
                    seed=seed,
                )
                for config in sorted(configs)
            ]
        with out.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    return 0


# --- codegen parity and the corpus manifest -----------------------------------------


def codegen_parity(mock_dir: Path, cuda_dir: Path) -> list[dict[str, Any]]:
    """Compare mock-H100 and real-device codegen records kernel by kernel."""
    rows = []
    for mock_path in sorted(Path(mock_dir).glob("L*__*.json")):
        if mock_path.name.endswith(".error.json"):
            continue
        cuda_path = Path(cuda_dir) / mock_path.name
        mock = json.loads(mock_path.read_text(encoding="utf-8"))
        if not cuda_path.exists():
            rows.append({"problem_id": mock["problem_id"], "parity": "missing-cuda-record"})
            continue
        real = json.loads(cuda_path.read_text(encoding="utf-8"))

        def signature(record: dict[str, Any]) -> list[tuple[str, str, str]]:
            return [
                (k["name"], k["source"], json.dumps(k["configs"], sort_keys=True))
                for k in record["kernels"]
            ]

        same_kernels = signature(mock) == signature(real)
        same_guards = mock["guards"] == real["guards"]
        rows.append(
            {
                "problem_id": mock["problem_id"],
                "parity": "identical" if same_kernels and same_guards else "differs",
                "kernels_identical": same_kernels,
                "guards_identical": same_guards,
            }
        )
    return rows


def corpus_manifest(root: Path, split_path: Path | None = None) -> dict[str, Any]:
    root = Path(root)
    split = json.loads(split_path.read_text(encoding="utf-8")) if split_path else None
    checks = {}
    for name in ("check_static", "check_compile", "check_compile_native", "check_interp"):
        file = root / f"{name}.json"
        if file.exists():
            checks[name] = {
                row["substrate_id"]: row
                for row in json.loads(file.read_text(encoding="utf-8"))["rows"]
            }
    rows = []
    for path in sorted(p for p in root.iterdir() if (p / "substrate.json").exists()):
        substrate = json.loads((path / "substrate.json").read_text(encoding="utf-8"))
        build = {}
        if (path / "build.json").exists():
            build = json.loads((path / "build.json").read_text(encoding="utf-8"))
        problem_id = substrate["problem_id"]
        if substrate["source_kind"] != "inductor":
            half = "evaluation"
        elif split is None:
            half = "unsplit"
        elif problem_id in split["calibration"]:
            half = "calibration"
        elif problem_id in split["evaluation"]:
            half = "evaluation"
        else:
            half = "excluded"
        rows.append(
            {
                "substrate_id": substrate["substrate_id"],
                "problem_id": problem_id,
                "level": substrate["level"],
                "source_kind": substrate["source_kind"],
                "source_revision": substrate["source_revision"],
                "source_license": substrate["source_license"],
                "kernel_sha256": sha256_file(path / "kernel.py"),
                "triton_coverage": build.get("triton_coverage"),
                "source_kernel_family": build.get("source_kernel_family"),
                "split_half": half,
                **{name: checks[name].get(path.name, {}).get("verdict") for name in checks},
            }
        )
    summary: dict[str, Any] = {"substrates": len(rows)}
    for key in ("source_kind", "split_half", *checks):
        counts: dict[str, int] = {}
        for row in rows:
            counts[str(row.get(key))] = counts.get(str(row.get(key)), 0) + 1
        summary[key] = counts
    return {
        "admission_version": ADMISSION_VERSION,
        "split_sha256": split.get("sha256") if split else None,
        "summary": summary,
        "rows": rows,
    }
