"""Record TorchInductor's Triton output for one KernelBench problem (S1 build step).

This module imports torch and triton and is meant to run inside the pinned
research image. It compiles a KernelBench ``Model`` with ``torch.compile``
(dynamic shapes, ``fullgraph=True``, inference under ``torch.no_grad()``) and
stops right after Inductor has written its output module, before any kernel is
compiled for or launched on a device. The returned *codegen record* is plain
JSON and holds everything :mod:`.inductor_convert` needs:

- the generated wrapper module source (``output_code``);
- for every Triton kernel: its source, the heuristic decorator's configs, grid
  expressions from Inductor's own ``GridExpr`` classes, and compile options;
- the Dynamo graph placeholders and the guard source of each one;
- the shape-environment guards, printed as Python, with the source of every
  symbol they mention;
- the AOTAutograd view/mutation metadata needed to decide whether the bare
  wrapper reproduces the module's output.

Two device modes exist. ``cuda`` uses the real device and needs a GPU job.
``mock-h100`` runs in a GPU-less container: it patches the handful of torch,
Triton and Dynamo entry points that query a CUDA driver so that codegen sees an
H100 SXM (sm_90, 132 SMs). No CUDA library is loaded and no kernel is compiled
or launched; tensors are fake. The patches are listed in :data:`MOCK_PATCHES`
and recorded in every record. Inductor's config choices depend on the device
properties in :data:`MOCK_H100_PROPERTIES`; the GPU admission step re-runs
codegen in ``cuda`` mode and compares the two records (``codegen_parity``).

Inductor settings (recorded per problem):

- ``torch._inductor.config.deterministic = True``: no on-device benchmarking
  that affects numerics; reductions get exactly one config and no
  ``dynamic_scale_rblock`` or coordinate-descent changes.
- ``triton.autotune_pointwise = False``: pointwise kernels get exactly one
  config, the one Inductor would launch.
- ``force_disable_caches = True``: no FX-graph, AOT or autotune cache reuse.
- Dynamo: ``assume_static_by_default = False`` and duck sizing off, so equal
  example sizes do not share a symbol; ``specialize_float = True``, so Python
  float inputs and attributes are compile-time constants (the substrate refuses
  a scalar input that differs from its native value).
- Matmul problems: optionally ``max_autotune=True`` with
  ``max_autotune_gemm_backends="TRITON"``. In deterministic mode Inductor picks
  the template with ``AlgorithmSelectorCache.pick_deterministic_choice``, without
  benchmarking, in both device modes (``gemm_choice_rule``).
"""

from __future__ import annotations

import ast
import contextlib
import dataclasses
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path
from types import ModuleType
from typing import Any

#: Device properties reported to Inductor in ``mock-h100`` mode. They are the
#: published values for an H100 SXM5 80GB (compute capability 9.0, 132 SMs,
#: 64K registers and 2048 threads per SM, 227 KB opt-in shared memory per block).
MOCK_H100_PROPERTIES: dict[str, Any] = {
    "name": "NVIDIA H100 80GB HBM3",
    "major": 9,
    "minor": 0,
    "multi_processor_count": 132,
    "total_memory": 85520809984,
    "regs_per_multiprocessor": 65536,
    "max_threads_per_multi_processor": 2048,
    "max_threads_per_block": 1024,
    "warp_size": 32,
    "shared_memory_per_block": 49152,
    "shared_memory_per_block_optin": 232448,
    "shared_memory_per_multiprocessor": 233472,
    "L2_cache_size": 52428800,
}

MOCK_PATCHES = (
    "torch.cuda.{is_available,device_count,current_device,get_device_properties,"
    "get_device_capability,get_device_name,_lazy_init,set_device,is_initialized,"
    "get_rng_state,set_rng_state}",
    "torch._C._cuda_getDevice",
    "torch.cuda.device.__enter__/__exit__ (no device switch)",
    "torch._dynamo.device_interface.CudaInterface device, stream and property queries",
    "torch.accelerator.is_available -> False (Dynamo stream tracking off)",
    "torch._subclasses.fake_tensor.init_gpu_context -> no-op",
    "triton.runtime.driver.active -> codegen-only driver targeting GPUTarget('cuda', 90, 32)",
    "Inductor joint-graph and post-grad pattern tables initialised before the patch is armed",
)

CODEGEN_RECORD_VERSION = "q1-inductor-codegen/1"


class CodegenError(RuntimeError):
    """Raised when a problem cannot be compiled into a convertible record."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


class _Captured(Exception):  # noqa: N818 - control-flow sentinel, not an error
    """Raised from the patched module loader once Inductor has written its output."""


# --- device mocking ------------------------------------------------------------

_MOCK_INSTALLED = False


def install_mock_h100() -> None:
    """Patch torch/Triton so Inductor generates sm_90 code without a CUDA driver.

    Must be called before the first ``torch.compile`` in the process. Refuses
    to run if a real CUDA device is visible, so a real device is never mocked.
    """
    global _MOCK_INSTALLED
    if _MOCK_INSTALLED:
        return
    import glob

    import torch

    if glob.glob("/dev/nvidia[0-9]*") or torch.cuda.is_available():
        raise CodegenError("mock-refused", "a CUDA device is visible; use mode='cuda'")

    import torch._subclasses.fake_tensor as fake_tensor_module
    from triton.backends.compiler import GPUTarget
    from triton.runtime.driver import driver as triton_driver

    class _CodegenOnlyDriver:
        """Answers target queries for codegen; never loads libcuda."""

        def get_current_target(self):
            return GPUTarget("cuda", 90, 32)

        def get_active_torch_device(self):
            return torch.device("cuda", 0)

        def get_current_device(self):
            return 0

        def get_current_stream(self, device=None):
            return 0

        def get_device_interface(self):
            return torch.cuda

        def is_active(self):
            return True

    class _Props:
        pass

    props = _Props()
    for key, value in MOCK_H100_PROPERTIES.items():
        setattr(props, key, value)
    props.gcnArchName = MOCK_H100_PROPERTIES["name"]
    props.uuid = "00000000-0000-0000-0000-000000000000"

    available = [False]
    torch.cuda.is_available = lambda: available[0]
    # Pattern tables are traced once per input device; trace them while CUDA is
    # still reported unavailable so no real CUDA tensor is ever created.
    import torch._inductor.fx_passes.joint_graph as joint_graph
    import torch._inductor.fx_passes.post_grad as post_grad

    fake_tensor_module.init_gpu_context = lambda device: None
    joint_graph.lazy_init(torch.device("cuda", 0))
    post_grad.lazy_init()

    triton_driver.set_active(_CodegenOnlyDriver())
    torch.cuda.device_count = lambda: 1
    torch.cuda.current_device = lambda: 0
    torch.cuda.get_device_properties = lambda *args, **kwargs: props
    torch.cuda.get_device_capability = lambda *args, **kwargs: (
        MOCK_H100_PROPERTIES["major"],
        MOCK_H100_PROPERTIES["minor"],
    )
    torch.cuda.get_device_name = lambda *args, **kwargs: MOCK_H100_PROPERTIES["name"]
    torch.cuda._lazy_init = lambda: None
    torch.cuda.set_device = lambda *args, **kwargs: None
    torch.cuda.is_initialized = lambda: True
    torch.cuda.get_rng_state = lambda *args, **kwargs: torch.zeros(16, dtype=torch.uint8)
    torch.cuda.set_rng_state = lambda *args, **kwargs: None
    torch._C._cuda_getDevice = lambda: 0
    torch.accelerator.is_available = lambda: False
    torch.cuda.device.__enter__ = lambda self: None
    torch.cuda.device.__exit__ = lambda self, *args: False
    # Dynamo's device interface binds torch.cuda functions at class creation.
    from torch._dynamo.device_interface import CudaInterface

    CudaInterface.current_device = staticmethod(lambda: 0)
    CudaInterface.set_device = staticmethod(lambda device: None)
    CudaInterface.device_count = staticmethod(lambda: 1)
    CudaInterface.get_device_properties = staticmethod(lambda device=None: props)
    CudaInterface.synchronize = staticmethod(lambda device=None: None)
    CudaInterface.memory_allocated = staticmethod(lambda device=None: 0)
    CudaInterface.is_bf16_supported = staticmethod(lambda *args, **kwargs: True)
    CudaInterface.exchange_device = staticmethod(lambda device: 0)
    CudaInterface.maybe_exchange_device = staticmethod(lambda device: 0)
    CudaInterface.get_raw_stream = staticmethod(lambda device: 0)
    available[0] = True
    _MOCK_INSTALLED = True


# --- problem loading -----------------------------------------------------------


def load_problem_module(path: Path, module_name: str = "kernelbench_problem") -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise CodegenError("problem-load-failed", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("Model", "get_inputs", "get_init_inputs"):
        if not hasattr(module, name):
            raise CodegenError("problem-load-failed", f"{path.name} lacks {name}")
    return module


def _meta_inputs(module: ModuleType) -> tuple[list[Any], str]:
    """Draw ``get_inputs()`` on the meta device (no allocation) when possible."""
    import torch

    try:
        with torch.device("meta"):
            values = list(module.get_inputs())
        return values, "meta"
    except Exception as exc:  # noqa: BLE001 - fall back to a real CPU draw
        meta_error = f"{type(exc).__name__}: {exc}"
    torch.manual_seed(42)
    values = list(module.get_inputs())
    return values, f"cpu (meta failed: {meta_error})"


# --- record helpers -------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    """Best-effort conversion of Inductor metadata to strict JSON."""
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        return (
            value if value == value and value not in (float("inf"), float("-inf")) else str(value)
        )
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple) and hasattr(value, "_asdict"):
        return {str(key): _jsonable(item) for key, item in value._asdict().items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted(str(item) for item in value)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)
        }
    if hasattr(value, "name") and hasattr(value, "value") and type(value).__module__ != "builtins":
        return str(value.name)
    return repr(value)


def _config_to_dict(config: Any) -> dict[str, Any]:
    if getattr(config, "pre_hook", None) is not None:
        raise CodegenError("config-pre-hook", "Inductor config carries a pre_hook")
    return {
        "kwargs": {key: _jsonable(value) for key, value in dict(config.kwargs).items()},
        "num_warps": int(config.num_warps),
        "num_stages": int(config.num_stages),
        "num_ctas": int(getattr(config, "num_ctas", 1) or 1),
        "maxnreg": getattr(config, "maxnreg", None),
    }


def _kernel_definitions(output_code: str) -> list[tuple[str, str]]:
    """Return ``(kernel_name, kernel_source)`` for every ``async_compile.triton`` call."""
    tree = ast.parse(output_code)
    found: list[tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "triton"
            and isinstance(func.value, ast.Name)
            and func.value.id == "async_compile"
        ):
            continue
        args = node.value.args
        if len(args) < 2 or not all(isinstance(arg, ast.Constant) for arg in args[:2]):
            raise CodegenError("unparsed-kernel", ast.unparse(node)[:200])
        found.append((str(args[0].value), str(args[1].value)))
    return found


def _kernel_function(kernel_source: str, kernel_name: str) -> ast.FunctionDef:
    for node in ast.parse(kernel_source).body:
        if isinstance(node, ast.FunctionDef) and node.name == kernel_name:
            return node
    raise CodegenError("unparsed-kernel", f"no def {kernel_name} in kernel source")


def _heuristic_decorator(function: ast.FunctionDef) -> ast.Call:
    for decorator in function.decorator_list:
        if (
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
            and decorator.func.value.id == "triton_heuristics"
        ):
            return decorator
    raise CodegenError("unparsed-kernel", f"{function.name} has no triton_heuristics decorator")


def _capture_kernel_meta(kernel_name: str, kernel_source: str) -> dict[str, Any]:
    """Evaluate the heuristic decorator with ``cached_autotune`` intercepted."""
    import torch._inductor.runtime.triton_heuristics as heuristics
    from torch._inductor.runtime import hints, triton_helpers
    from torch.utils._ordered_set import OrderedSet

    function = _kernel_function(kernel_source, kernel_name)
    decorator = _heuristic_decorator(function)
    captured: dict[str, Any] = {}

    def fake_cached_autotune(
        size_hints,
        configs,
        triton_meta,
        heuristic_type,
        filename=None,
        inductor_meta=None,
        **kwargs,
    ):
        captured.update(
            size_hints=size_hints,
            configs=list(configs),
            triton_meta=triton_meta,
            heuristic_type=heuristic_type,
            inductor_meta=dict(inductor_meta or {}),
        )
        return lambda fn: fn

    namespace = {
        "triton_heuristics": heuristics,
        "triton_helpers": triton_helpers,
        "DeviceProperties": hints.DeviceProperties,
        "AutotuneHint": hints.AutotuneHint,
        "ReductionHint": hints.ReductionHint,
        "TileHint": hints.TileHint,
        "OrderedSet": OrderedSet,
        "__file__": f"{kernel_name}.py",
    }
    original = heuristics.cached_autotune
    heuristics.cached_autotune = fake_cached_autotune
    try:
        eval(compile(ast.Expression(decorator), f"<{kernel_name}>", "eval"), namespace)  # noqa: S307
    finally:
        heuristics.cached_autotune = original
    if "configs" not in captured:
        raise CodegenError(
            "unparsed-kernel", f"{kernel_name}: heuristic did not reach cached_autotune"
        )

    params = [arg.arg for arg in function.args.args]
    constexpr_params = [
        arg.arg
        for arg in function.args.args
        if arg.annotation is not None and "constexpr" in ast.unparse(arg.annotation)
    ]
    configs = []
    for config in captured["configs"]:
        record = _config_to_dict(config)
        if "XBLOCK" not in params and "XBLOCK" in record["kwargs"]:
            # cached_autotune's decorator drops XBLOCK when no_x_dim is set.
            if record["kwargs"]["XBLOCK"] != 1:
                raise CodegenError("unparsed-kernel", f"{kernel_name}: XBLOCK != 1 without x dim")
            record["kwargs"].pop("XBLOCK")
        configs.append(record)
    inductor_meta = captured["inductor_meta"]
    triton_meta = captured["triton_meta"]
    grid = _grid_expressions(inductor_meta, configs[0]["kwargs"]) if configs else None
    compile_options = {
        "debug": bool(inductor_meta.get("assert_indirect_indexing", True)),
        "sanitize_overflow": False,
        "enable_fp_fusion": bool(triton_meta.get("enable_fp_fusion", True)),
        "launch_cooperative_grid": bool(triton_meta.get("launch_cooperative_grid", False)),
        "launch_pdl": bool(triton_meta.get("launch_pdl", False)),
        "enable_reflect_ftz": not bool(triton_meta.get("disable_ftz", False)),
    }
    return {
        "name": kernel_name,
        "source": kernel_source,
        "params": params,
        "constexpr_params": constexpr_params,
        "heuristic_type": str(
            getattr(captured["heuristic_type"], "name", captured["heuristic_type"])
        ),
        "heuristic": decorator.func.attr,
        "size_hints": _jsonable(captured["size_hints"]),
        "configs": configs,
        "grid_type": inductor_meta.get("grid_type"),
        "grid": grid,
        "signature": _jsonable(triton_meta.get("signature", {})),
        "constants": _jsonable(triton_meta.get("constants", {})),
        "compile_options": compile_options,
        "inductor_meta": _jsonable(inductor_meta),
        "device": _jsonable(triton_meta.get("device")),
    }


def _grid_expressions(
    inductor_meta: dict[str, Any], config_kwargs: dict[str, Any]
) -> dict[str, Any]:
    """Inductor's own grid expressions with block sizes left symbolic and ``triton.cdiv``."""
    from torch._inductor.runtime import triton_heuristics as heuristics

    grid_type = inductor_meta.get("grid_type")
    if grid_type is None:
        raise CodegenError("unsupported-grid", "kernel has no grid_type")
    original = heuristics.GridExpr.ceildiv

    def cdiv(self, numel, block):
        if block is None or block == 1:
            return numel
        if isinstance(numel, int) and isinstance(block, int):
            return original(self, numel, block)
        return f"triton.cdiv({numel}, {block})"

    heuristics.GridExpr.ceildiv = cdiv
    try:
        symbolic = {key: key for key in config_kwargs}
        grid = heuristics.GridExpr.from_meta(inductor_meta, symbolic)
    except Exception as exc:  # noqa: BLE001 - recorded as an unsupported grid
        raise CodegenError("unsupported-grid", f"{grid_type}: {type(exc).__name__}: {exc}") from exc
    finally:
        heuristics.GridExpr.ceildiv = original
    return {
        "type": grid_type,
        "prefix": list(grid.prefix),
        "x": str(grid.x_grid),
        "y": str(grid.y_grid),
        "z": str(grid.z_grid),
    }


def _fw_metadata_summary(metadata: Any) -> dict[str, Any]:
    if metadata is None:
        return {"available": False}
    output_types = [
        str(getattr(info.output_type, "name", info.output_type))
        for info in getattr(metadata, "output_info", [])
    ]
    mutated_runtime = list(getattr(metadata, "mutated_inp_runtime_indices", []) or [])
    input_info = getattr(metadata, "input_info", []) or []
    mutated_in_graph = [
        index
        for index, info in enumerate(input_info)
        if getattr(info, "mutates_data", False) or getattr(info, "mutates_metadata", False)
    ]
    return {
        "available": True,
        "output_types": output_types,
        "mutated_inp_runtime_indices": mutated_runtime,
        "mutated_inputs": mutated_in_graph,
        "num_intermediate_bases": int(getattr(metadata, "num_intermediate_bases", 0) or 0),
        "is_rng_op_functionalized": bool(getattr(metadata, "is_rng_op_functionalized", False)),
        "num_outputs_rng_offset": int(getattr(metadata, "num_outputs_rng_offset", 0) or 0),
        "keep_input_mutations": bool(getattr(metadata, "keep_input_mutations", False)),
    }


def _finite_int(value: Any) -> int | None:
    """``int(value)`` for a finite sympy bound; ``None`` for (int) infinities."""
    if "oo" in str(value):
        return None
    return int(value)


def _guards(shape_env: Any, placeholder_symbols: list[Any]) -> dict[str, Any]:
    """Shape guards as Python, plus the value range Dynamo assumed for every symbol.

    The range lower bound is usually 2: Dynamo specialises sizes 0 and 1, so the
    compiled code was only ever valid for sizes of at least 2.
    """
    import sympy
    from torch.utils._sympy.printers import PythonPrinter

    printer = PythonPrinter()
    rows = []
    symbols: set[Any] = set(placeholder_symbols)
    for guard in getattr(shape_env, "guards", []):
        expr = guard.expr
        if expr in (sympy.true, True):
            continue
        rows.append(printer.doprint(expr))
        symbols |= set(expr.free_symbols)
    sources = {}
    ranges = {}
    for symbol in sorted(symbols, key=str):
        candidates = shape_env.var_to_sources.get(symbol) or []
        if not candidates:
            raise CodegenError("unbound-guard-symbol", str(symbol))
        sources[str(symbol)] = candidates[0].name
        value_range = shape_env.var_to_range.get(symbol)
        if value_range is not None:
            ranges[str(symbol)] = [_finite_int(value_range.lower), _finite_int(value_range.upper)]
    hints = {
        str(symbol): int(value)
        for symbol, value in shape_env.var_to_val.items()
        if str(symbol) in sources
    }
    return {
        "expressions": sorted(set(rows)),
        "symbol_sources": sources,
        "symbol_hints": hints,
        "symbol_ranges": ranges,
    }


def _output_structure(value: Any) -> dict[str, Any]:
    import torch

    if isinstance(value, torch.Tensor):
        return {"kind": "tensor", "count": 1}
    if isinstance(value, tuple | list) and all(isinstance(item, torch.Tensor) for item in value):
        return {"kind": type(value).__name__, "count": len(value)}
    return {"kind": f"unsupported:{type(value).__name__}", "count": 0}


def _sources_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- main entry ------------------------------------------------------------------


@contextlib.contextmanager
def _inductor_settings(max_autotune_gemm: bool, constant_folding: bool = True):
    import torch._dynamo
    import torch._inductor.config as inductor_config
    import torch.fx.experimental._config as fx_config

    saved = {
        "deterministic": inductor_config.deterministic,
        "autotune_pointwise": inductor_config.triton.autotune_pointwise,
        "force_disable_caches": inductor_config.force_disable_caches,
        "max_autotune": inductor_config.max_autotune,
        "max_autotune_gemm_backends": inductor_config.max_autotune_gemm_backends,
        "assume_static_by_default": torch._dynamo.config.assume_static_by_default,
        "specialize_float": torch._dynamo.config.specialize_float,
        "use_duck_shape": fx_config.use_duck_shape,
        "joint_graph_constant_folding": inductor_config.joint_graph_constant_folding,
    }
    inductor_config.deterministic = True
    inductor_config.triton.autotune_pointwise = False
    inductor_config.force_disable_caches = True
    if max_autotune_gemm:
        inductor_config.max_autotune = True
        inductor_config.max_autotune_gemm_backends = "TRITON"
    torch._dynamo.config.assume_static_by_default = False
    torch._dynamo.config.specialize_float = True
    fx_config.use_duck_shape = False
    inductor_config.joint_graph_constant_folding = constant_folding
    try:
        yield {
            "deterministic": True,
            "triton.autotune_pointwise": False,
            "force_disable_caches": True,
            "max_autotune": bool(max_autotune_gemm),
            "max_autotune_gemm_backends": "TRITON"
            if max_autotune_gemm
            else saved["max_autotune_gemm_backends"],
            "dynamo.assume_static_by_default": False,
            "dynamo.specialize_float": True,
            "fx.use_duck_shape": False,
            "joint_graph_constant_folding": constant_folding,
            "dynamic": True,
            "fullgraph": True,
            "grad_mode": "no_grad",
        }
    finally:
        inductor_config.deterministic = saved["deterministic"]
        inductor_config.triton.autotune_pointwise = saved["autotune_pointwise"]
        inductor_config.force_disable_caches = saved["force_disable_caches"]
        inductor_config.max_autotune = saved["max_autotune"]
        inductor_config.max_autotune_gemm_backends = saved["max_autotune_gemm_backends"]
        torch._dynamo.config.assume_static_by_default = saved["assume_static_by_default"]
        torch._dynamo.config.specialize_float = saved["specialize_float"]
        fx_config.use_duck_shape = saved["use_duck_shape"]
        inductor_config.joint_graph_constant_folding = saved["joint_graph_constant_folding"]


def codegen_problem(
    problem_path: Path,
    problem_id: str,
    *,
    mode: str = "mock-h100",
    max_autotune_gemm: bool = False,
    constant_folding: bool = True,
) -> dict[str, Any]:
    """Compile one problem and return its codegen record (raises :class:`CodegenError`)."""
    import torch
    import torch._dynamo
    import triton
    from torch._inductor import codecache

    if mode == "mock-h100":
        install_mock_h100()
    elif mode != "cuda":
        raise ValueError(f"unknown mode {mode!r}")

    started = time.monotonic()
    torch._dynamo.reset()
    module = load_problem_module(problem_path)
    meta_inputs, input_draw = _meta_inputs(module)

    state: dict[str, Any] = {}

    def backend(graph_module, example_inputs):
        from torch._guards import detect_fake_mode
        from torch._inductor.compile_fx import compile_fx

        placeholders = []
        for node in graph_module.graph.nodes:
            if node.op != "placeholder":
                continue
            grapharg = node.meta.get("grapharg")
            example = node.meta.get("example_value")
            if grapharg is None:
                raise CodegenError("placeholder-without-source", node.name)
            if isinstance(example, torch.Tensor):
                kind = {
                    "kind": "tensor",
                    "dtype": str(example.dtype).replace("torch.", ""),
                    "ndim": example.dim(),
                    "device_type": example.device.type,
                }
            elif isinstance(example, torch.SymInt | int):
                kind = {"kind": "int"}
                if isinstance(example, torch.SymInt):
                    state.setdefault("placeholder_symbols", []).append(example.node.expr)
            elif isinstance(example, torch.SymFloat | float):
                kind = {"kind": "float"}
            else:
                kind = {"kind": f"other:{type(example).__name__}"}
            placeholders.append({"name": node.name, "source": grapharg.source.name, **kind})
        state["placeholders"] = placeholders
        fake_mode = detect_fake_mode(example_inputs)
        state["shape_env"] = getattr(fake_mode, "shape_env", None)
        output_node = next(node for node in graph_module.graph.nodes if node.op == "output")
        outputs = output_node.args[0]
        state["graph_outputs"] = len(outputs) if isinstance(outputs, tuple | list) else 1
        return compile_fx(graph_module, example_inputs)

    original_loader = codecache.PyCodeCache.load_by_key_path

    def capture_loader(key, path, *args, **kwargs):
        from torch._guards import TracingContext

        text = Path(path).read_text(encoding="utf-8")
        if "def call(" not in text:
            # A template benchmark module, not the wrapper; record and pass through.
            state.setdefault("passthrough_modules", []).append(text[:200])
            return original_loader(key, path, *args, **kwargs)
        state["output_code"] = text
        context = TracingContext.try_get()
        state["fw_metadata"] = _fw_metadata_summary(getattr(context, "fw_metadata", None))
        raise _Captured()

    gemm_rule = None
    from torch._subclasses.fake_tensor import FakeTensorMode
    from torch.fx.experimental.symbolic_shapes import ShapeEnv

    with (
        _inductor_settings(max_autotune_gemm, constant_folding) as settings,
        contextlib.ExitStack() as stack,
    ):
        if max_autotune_gemm:
            gemm_rule = (
                "AlgorithmSelectorCache.pick_deterministic_choice "
                "(Inductor deterministic mode; no benchmarking)"
            )
        codecache.PyCodeCache.load_by_key_path = capture_loader
        stack.callback(setattr, codecache.PyCodeCache, "load_by_key_path", original_loader)
        torch.manual_seed(42)
        model = module.Model(*module.get_init_inputs())
        fake_mode = FakeTensorMode(shape_env=ShapeEnv(), allow_non_fake_inputs=True)
        error: BaseException | None = None
        with fake_mode, torch.no_grad():
            fake_inputs = [
                torch.empty_strided(value.shape, value.stride(), dtype=value.dtype, device="cuda")
                if isinstance(value, torch.Tensor)
                else value
                for value in meta_inputs
            ]
            model = _fake_module(model, fake_mode)
            module_types = sorted({type(child).__name__ for child in model.modules()})
            eager_structure = _output_structure(model(*fake_inputs))
            compiled = torch.compile(model, backend=backend, dynamic=True, fullgraph=True)
            try:
                compiled(*fake_inputs)
            except _Captured:
                pass
            except Exception as exc:  # noqa: BLE001 - classified below
                error = exc
        if "output_code" not in state:
            detail = (
                "".join(traceback.format_exception_only(type(error), error)).strip()
                if error
                else ""
            )
            cause = error
            while cause is not None and not isinstance(cause, _Captured | CodegenError):
                cause = cause.__cause__ or cause.__context__
            if isinstance(cause, CodegenError):
                raise cause
            if error is not None and "Unsupported" in type(error).__name__:
                raise CodegenError("graph-break", detail[-2000:])
            raise CodegenError("compile-failed", detail[-2000:])

    output_code = state["output_code"]
    kernels = [
        _capture_kernel_meta(name, source) for name, source in _kernel_definitions(output_code)
    ]
    if state.get("shape_env") is None:
        raise CodegenError("no-shape-env")
    guards = _guards(state["shape_env"], state.get("placeholder_symbols", []))
    return {
        "record_version": CODEGEN_RECORD_VERSION,
        "problem_id": problem_id,
        "problem_path": problem_path.name,
        "problem_source": _sources_text(problem_path),
        "mode": mode,
        "device_properties": MOCK_H100_PROPERTIES
        if mode == "mock-h100"
        else _real_device_properties(),
        "mock_patches": list(MOCK_PATCHES) if mode == "mock-h100" else [],
        "settings": settings,
        "gemm_choice_rule": gemm_rule,
        "input_draw": input_draw,
        "inputs": [
            {
                "kind": "tensor",
                "shape": list(value.shape),
                "dtype": str(value.dtype).replace("torch.", ""),
            }
            if isinstance(value, torch.Tensor)
            else {"kind": type(value).__name__, "value": _jsonable(value)}
            for value in meta_inputs
        ],
        "placeholders": state["placeholders"],
        "graph_outputs": state["graph_outputs"],
        "eager_output": eager_structure,
        "module_types": module_types,
        "fw_metadata": state["fw_metadata"],
        "guards": guards,
        "output_code": output_code,
        "kernels": kernels,
        "versions": {
            "torch": torch.__version__,
            "torch_git": torch.version.git_version,
            "triton": triton.__version__,
            "python": sys.version.split()[0],
        },
        "codegen_seconds": round(time.monotonic() - started, 3),
    }


def _fake_module(model: Any, fake_mode: Any) -> Any:
    """Replace every parameter and buffer by a fake CUDA tensor with the same values' metadata."""
    import torch

    for module in model.modules():
        for name, param in list(module._parameters.items()):
            if param is not None:
                fake = fake_mode.from_tensor(param.detach()).to("cuda")
                module._parameters[name] = torch.nn.Parameter(
                    fake, requires_grad=param.requires_grad
                )
        for name, buffer in list(module._buffers.items()):
            if buffer is not None:
                module._buffers[name] = fake_mode.from_tensor(buffer).to("cuda")
    return model


def _real_device_properties() -> dict[str, Any]:
    import torch

    props = torch.cuda.get_device_properties(torch.cuda.current_device())
    return {key: getattr(props, key, None) for key in MOCK_H100_PROPERTIES}


def write_record(record: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(record, indent=1, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    tmp.replace(path)
