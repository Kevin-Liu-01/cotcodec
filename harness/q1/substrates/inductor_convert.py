"""Convert a TorchInductor codegen record into an S1 substrate directory.

Pure Python (``ast`` only): no torch or triton import, so it runs and is tested
anywhere. Input is the JSON record written by :mod:`.inductor_codegen`.

What the conversion does, and nothing else:

1. Copies each Triton kernel's source verbatim and removes only its
   ``@triton_heuristics.<kind>(...)`` decorator, keeping ``@triton.jit``.
2. Rewrites each ``kernel.run(*args, stream=streamN)`` in Inductor's ``call``
   into ``kernel[_grid_kernel](*args, <config>, <Inductor compile options>)``,
   a plain JIT launch that goes through ``JITFunction.__getitem__`` and
   ``JITFunction.run``, which gate (b)'s launch hook patches. The config is the
   single one Inductor's heuristic yields in deterministic mode; the compile
   options are the ones ``CachingAutotuner._create_compile_options`` would pass
   (``debug``, ``sanitize_overflow=False`` and any non-default flags).
3. Builds each grid from Inductor's own ``GridExpr`` strings (recorded by the
   codegen step) with block sizes bound from the launch metadata.
4. Replaces the hard-coded device index 0 with the inputs' device and drops the
   raw-stream lookups (launches use the current stream, as Inductor's do).
5. Turns Dynamo's tensor guards (dtype, rank, device type) and the shape
   environment's guards into :class:`SubstrateRefusal` checks that run before
   any launch, so an input outside the compiled specialisation is refused
   instead of computed wrongly. ``assert_size_stride`` stays as Inductor wrote it.
6. Wraps everything in ``class ModelNew(Model)``: the reference ``Model`` from
   the KernelBench file is embedded (``ast.unparse``, docstrings dropped), so
   ``__init__`` (and its RNG draws) is identical; ``forward`` binds the Dynamo
   graph inputs from their guard sources (for example ``L['x'].size()[0]``) and
   calls the wrapper.

Records that cannot be converted faithfully raise :class:`ConversionError`
with a stable reason code; the build logs the problem as excluded.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any

from harness.q1.schema import (
    KERNELBENCH_PROBLEMS_REVISION,
    SCHEMA_VERSION,
    parse_problem_id,
    validate_substrate,
)
from harness.q1.substrates.sources import SOURCES

CONVERTER_VERSION = "q1-inductor-convert/1"

#: Names a grid expression may use without binding them from the launch metadata.
GRID_BUILTINS = {"triton", "max", "min", "int"}

#: Module types whose forward depends on ``self.training``; a substrate compiled
#: from such a module refuses to run in eval mode instead of computing the
#: training-mode graph.
TRAINING_DEPENDENT_MODULES = {
    "BatchNorm1d",
    "BatchNorm2d",
    "BatchNorm3d",
    "SyncBatchNorm",
    "Dropout",
    "Dropout1d",
    "Dropout2d",
    "Dropout3d",
    "AlphaDropout",
    "FeatureAlphaDropout",
}

#: Prelude statements that only Inductor's async compiler, profiler or
#: distributed paths need; never copied.
_DROPPED_PRELUDE_NAMES = {"AsyncCompile", "async_compile", "empty_strided_p2p"}


class ConversionError(ValueError):
    """The record cannot be converted faithfully; ``reason`` is a stable code."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


@dataclass
class ConvertedSubstrate:
    substrate_id: str
    kernel_py: str
    substrate_json: dict[str, Any]
    build_json: dict[str, Any]
    extra_files: dict[str, str] = field(default_factory=dict)

    def files(self) -> dict[str, str]:
        out = {"kernel.py": self.kernel_py, **self.extra_files}
        out["build.json"] = json.dumps(self.build_json, indent=1, sort_keys=True) + "\n"
        return out


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def substrate_id_for(problem_id: str, prefix: str = "s1-inductor") -> str:
    level, number, name = parse_problem_id(problem_id)
    return f"{prefix}-L{level}-{number}_{name}"


# --- problem source ------------------------------------------------------------


def _strip_docstrings(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                node.body = body[1:] or [ast.Expr(ast.Constant(None))]


def reference_model_source(problem_source: str) -> tuple[str, ast.FunctionDef]:
    """The problem file without ``get_inputs``/``get_init_inputs`` or docstrings, and ``forward``.

    The reference is re-emitted with ``ast.unparse`` (comments and docstrings
    dropped), because KernelBench's static checker matches ``pass``/``except`` in
    prose such as "Forward pass" and would reject the substrate for its packaging.
    """
    tree = ast.parse(problem_source)
    forward: ast.FunctionDef | None = None
    kept: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("get_inputs", "get_init_inputs"):
            continue
        if isinstance(node, ast.ClassDef) and node.name == "ModelNew":
            raise ConversionError("problem-defines-modelnew")
        if isinstance(node, ast.ClassDef) and node.name == "Model":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "forward":
                    forward = item
        kept.append(node)
    if forward is None:
        raise ConversionError("problem-without-forward")
    module = ast.Module(body=kept, type_ignores=[])
    _strip_docstrings(module)
    return ast.unparse(module).rstrip() + "\n", forward


def forward_signature(forward: ast.FunctionDef) -> tuple[str, list[str]]:
    """Return the ``forward`` argument list text and its parameter names (without self)."""
    arguments = forward.args
    if arguments.vararg or arguments.kwarg or arguments.kwonlyargs or arguments.posonlyargs:
        raise ConversionError("unsupported-forward-signature", ast.unparse(arguments))
    names = [arg.arg for arg in arguments.args]
    if not names or names[0] != "self":
        raise ConversionError("unsupported-forward-signature", "first argument is not self")
    return ast.unparse(arguments), names[1:]


# --- kernels -------------------------------------------------------------------


def _segment(lines: list[str], node: ast.FunctionDef) -> str:
    start = min([node.lineno] + [d.lineno for d in node.decorator_list])
    return "\n".join(lines[start - 1 : node.end_lineno]) + "\n"


def _kernel_text(kernel: dict[str, Any]) -> tuple[list[str], str, dict[str, str]]:
    """Return (import lines, kernel text with only the heuristic decorator removed, helpers).

    ``helpers`` maps the name of every other ``@triton.jit`` function in the kernel
    module (for example the combine function of ``tl.associative_scan``) to its
    verbatim text.
    """
    source = kernel["source"]
    tree = ast.parse(source)
    lines = source.splitlines()
    imports: list[str] = []
    function: ast.FunctionDef | None = None
    others: list[ast.stmt] = []
    helpers: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            imports.append(ast.unparse(node))
        elif isinstance(node, ast.FunctionDef) and node.name == kernel["name"]:
            function = node
        elif isinstance(node, ast.FunctionDef) and [
            ast.unparse(d) for d in node.decorator_list
        ] == ["triton.jit"]:
            helpers[node.name] = _segment(lines, node)
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and ast.unparse(node.value.func) == "triton_helpers.set_driver_to_gpu"
        ):
            continue
        else:
            others.append(node)
    if function is None:
        raise ConversionError("unparsed-kernel", kernel["name"])
    if others:
        raise ConversionError(
            "unexpected-kernel-module-code", f"{kernel['name']}: {ast.unparse(others[0])[:120]}"
        )
    heuristic = [
        d
        for d in function.decorator_list
        if isinstance(d, ast.Call) and ast.unparse(d.func).startswith("triton_heuristics.")
    ]
    jit = [d for d in function.decorator_list if ast.unparse(d) == "triton.jit"]
    if len(heuristic) != 1 or len(jit) != 1 or len(function.decorator_list) != 2:
        raise ConversionError(
            "unexpected-decorators",
            f"{kernel['name']}: {[ast.unparse(d)[:40] for d in function.decorator_list]}",
        )
    dropped = set(range(heuristic[0].lineno, (heuristic[0].end_lineno or 0) + 1))
    start = min(d.lineno for d in function.decorator_list)
    body = [
        lines[index - 1]
        for index in range(start, (function.end_lineno or function.lineno) + 1)
        if index not in dropped
    ]
    return imports, "\n".join(body) + "\n", helpers


def _normalise_kernel_imports(import_lines: list[str]) -> list[str]:
    """Kernel-module imports minus triton_heuristics and Inductor hint classes."""
    kept: list[str] = []
    for line in import_lines:
        node = ast.parse(line).body[0]
        if isinstance(node, ast.ImportFrom) and node.module == "torch._inductor.runtime.hints":
            continue
        if isinstance(node, ast.ImportFrom):
            names = [alias for alias in node.names if alias.name != "triton_heuristics"]
            if not names:
                continue
            node.names = names
        kept.append(ast.unparse(node))
    return kept


def _choose_config(kernel: dict[str, Any]) -> tuple[dict[str, Any], str]:
    configs = kernel.get("configs") or []
    if not configs:
        raise ConversionError("no-config", kernel["name"])
    rule = "single-config" if len(configs) == 1 else f"first-of-{len(configs)}"
    return configs[0], rule


def _extra_launcher_args(kernel: dict[str, Any]) -> list[str]:
    meta = kernel.get("inductor_meta") or {}
    return list(meta.get("extra_launcher_args") or [])


def _grid_function(kernel: dict[str, Any], config: dict[str, Any]) -> str:
    grid = kernel.get("grid")
    if not grid:
        raise ConversionError("unsupported-grid", f"{kernel['name']}: no grid recorded")
    if grid["type"] == "FixedGrid":
        extra = _extra_launcher_args(kernel)
        if [grid["x"], grid["y"], grid["z"]] != extra[:3] or len(extra) != 3:
            raise ConversionError("unsupported-grid", f"{kernel['name']}: FixedGrid {grid}")
        return ""
    allowed = set(kernel["params"]) | set(config["kwargs"])
    assigned: list[str] = []
    needed: list[str] = []
    statements: list[str] = []
    for line in grid.get("prefix", []):
        node = ast.parse(line).body[0]
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            raise ConversionError("unsupported-grid", f"{kernel['name']}: prefix {line!r}")
        statements.append(ast.unparse(node))
        _collect_names(node.value, assigned, needed)
        assigned.append(ast.unparse(node.targets[0]))
    axes = []
    for axis in ("x", "y", "z"):
        expr = ast.parse(str(grid[axis]), mode="eval").body
        _collect_names(expr, assigned, needed)
        axes.append(ast.unparse(expr))
    missing = [name for name in needed if name not in allowed]
    if missing:
        raise ConversionError("unsupported-grid", f"{kernel['name']}: unbound {missing}")
    binds = [f'    {name} = META["{name}"]' for name in needed]
    body = binds + [f"    {statement}" for statement in statements]
    body.append(f"    return ({axes[0]}, {axes[1]}, {axes[2]})")
    header = f"def _grid_{kernel['name']}(META):"
    doc = f'    """Grid from Inductor GridExpr {grid["type"]} (ceil division as triton.cdiv)."""'
    return "\n".join([header, doc, *body]) + "\n"


def _collect_names(node: ast.AST, assigned: list[str], needed: list[str]) -> None:
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Name)
            and child.id not in GRID_BUILTINS
            and child.id not in assigned
            and child.id not in needed
        ):
            needed.append(child.id)


def _launch_keywords(kernel: dict[str, Any], config: dict[str, Any]) -> list[ast.keyword]:
    constexprs = set(kernel["constexpr_params"])
    keywords: list[ast.keyword] = []
    for name, value in config["kwargs"].items():
        if name not in constexprs:
            raise ConversionError("config-kwarg-not-constexpr", f"{kernel['name']}.{name}")
        keywords.append(ast.keyword(arg=name, value=ast.Constant(value)))
    keywords.append(ast.keyword(arg="num_warps", value=ast.Constant(config["num_warps"])))
    keywords.append(ast.keyword(arg="num_stages", value=ast.Constant(config["num_stages"])))
    if config.get("num_ctas", 1) != 1:
        keywords.append(ast.keyword(arg="num_ctas", value=ast.Constant(config["num_ctas"])))
    if config.get("maxnreg") is not None:
        keywords.append(ast.keyword(arg="maxnreg", value=ast.Constant(config["maxnreg"])))
    options = kernel["compile_options"]
    keywords.append(ast.keyword(arg="debug", value=ast.Constant(bool(options["debug"]))))
    keywords.append(ast.keyword(arg="sanitize_overflow", value=ast.Constant(False)))
    defaults = {
        "enable_fp_fusion": True,
        "launch_cooperative_grid": False,
        "launch_pdl": False,
        "enable_reflect_ftz": True,
    }
    for name, default in defaults.items():
        if bool(options.get(name, default)) != default:
            keywords.append(ast.keyword(arg=name, value=ast.Constant(not default)))
    return keywords


# --- the call wrapper ------------------------------------------------------------


class _CallRewriter(ast.NodeTransformer):
    def __init__(self, kernels: dict[str, dict[str, Any]], configs: dict[str, dict[str, Any]]):
        self.kernels = kernels
        self.configs = configs
        self.launches: dict[str, int] = {}
        self.stream_names: set[str] = set()

    def visit_Assign(self, node: ast.Assign) -> ast.AST | None:  # noqa: N802 - ast API
        if (
            isinstance(node.value, ast.Call)
            and ast.unparse(node.value.func) == "get_raw_stream"
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            self.stream_names.add(node.targets[0].id)
            return None
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> ast.AST:  # noqa: N802 - ast API
        self.generic_visit(node)
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "run"
            and isinstance(func.value, ast.Name)
        ):
            name = func.value.id
            if name not in self.kernels:
                raise ConversionError("unconverted-launch", ast.unparse(node)[:160])
            kernel = self.kernels[name]
            config = self.configs[name]
            runtime_params = [p for p in kernel["params"] if p not in kernel["constexpr_params"]]
            keywords = [k for k in node.keywords if k.arg != "stream"]
            if any(k.arg is None for k in keywords):
                raise ConversionError("launch-arity", f"{name}: **kwargs at launch")
            args = list(node.args)
            if kernel["grid"]["type"] == "FixedGrid":
                # Template kernels receive their grid as trailing launcher arguments.
                if keywords or len(args) != len(runtime_params) + 3:
                    raise ConversionError("launch-arity", f"{name}: FixedGrid launch {len(args)}")
                grid: ast.expr = ast.Tuple(elts=args[-3:], ctx=ast.Load())
                args = args[:-3]
            else:
                grid = ast.Name(f"_grid_{name}", ast.Load())
            if len(args) + len(keywords) != len(runtime_params):
                raise ConversionError(
                    "launch-arity",
                    f"{name}: {len(args) + len(keywords)} args for {len(runtime_params)} "
                    "runtime parameters",
                )
            self.launches[name] = self.launches.get(name, 0) + 1
            return ast.Call(
                func=ast.Subscript(value=ast.Name(name, ast.Load()), slice=grid, ctx=ast.Load()),
                args=args,
                keywords=keywords + _launch_keywords(kernel, config),
            )
        text = ast.unparse(func)
        if text in ("torch.cuda._DeviceGuard", "torch.cuda.set_device"):
            if len(node.args) != 1 or ast.unparse(node.args[0]) != "0":
                raise ConversionError("unexpected-device-index", ast.unparse(node))
            node.args = [ast.Name("device_index", ast.Load())]
        return node


def _find_call_function(output_code: str) -> ast.FunctionDef:
    tree = ast.parse(output_code)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Runner":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "call":
                    return item
        if isinstance(node, ast.FunctionDef) and node.name == "call":
            return node
    raise ConversionError("no-call-function")


def _prelude_statements(output_code: str) -> list[ast.stmt]:
    """Module statements before the first kernel definition."""
    tree = ast.parse(output_code)
    prelude: list[ast.stmt] = []
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and ast.unparse(node.value.func) == "async_compile.triton"
        ):
            break
        prelude.append(node)
    return prelude


def _bound_names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.Import | ast.ImportFrom):
        return [(alias.asname or alias.name).split(".")[0] for alias in node.names]
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    return []


def _used_names(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _rewrite_call(record: dict[str, Any], configs: dict[str, dict[str, Any]]) -> tuple[str, dict]:
    kernels = {kernel["name"]: kernel for kernel in record["kernels"]}
    function = _find_call_function(record["output_code"])
    rewriter = _CallRewriter(kernels, configs)
    function = rewriter.visit(function)
    body = ast.Module(body=function.body, type_ignores=[])
    if "self" in _used_names(body):
        raise ConversionError("partitioned-wrapper", "call body references self")
    unpack = next(
        (
            stmt
            for stmt in function.body
            if isinstance(stmt, ast.Assign)
            and isinstance(stmt.value, ast.Name)
            and stmt.value.id == "args"
        ),
        None,
    )
    if unpack is None or not isinstance(unpack.targets[0], ast.Tuple | ast.Name):
        raise ConversionError("call-arity", "no 'a, b = args' unpack in call")
    target = unpack.targets[0]
    arity = len(target.elts) if isinstance(target, ast.Tuple) else 1
    if arity != len(record["placeholders"]):
        raise ConversionError(
            "call-arity",
            f"call unpacks {arity} args for {len(record['placeholders'])} placeholders",
        )
    for name in rewriter.stream_names:
        if name in _used_names(ast.Module(body=function.body, type_ignores=[])):
            raise ConversionError("stream-in-use", name)
    missing_launch = sorted(set(kernels) - set(rewriter.launches))
    if missing_launch:
        raise ConversionError("kernel-never-launched", ", ".join(missing_launch))
    function.name = "call"
    function.args = ast.arguments(
        posonlyargs=[],
        args=[ast.arg("args"), ast.arg("device_index")],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )
    function.decorator_list = []
    function.returns = None
    ast.fix_missing_locations(function)
    extern = sorted(
        {
            ast.unparse(n.func)
            for n in ast.walk(function)
            if isinstance(n, ast.Call)
            and re.match(r"^(extern_kernels|aten|torch\.ops)\.", ast.unparse(n.func))
        }
    )
    return ast.unparse(function) + "\n", {"launches": rewriter.launches, "library_calls": extern}


# --- guards ----------------------------------------------------------------------


def _guard_function(guards: dict[str, Any]) -> tuple[str, list[str]]:
    expressions = list(guards.get("expressions", []))
    symbols = sorted(guards.get("symbol_sources", {}))
    for expression in expressions:
        tree = ast.parse(expression, mode="eval")
        free = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        unknown = free - set(symbols) - {"math", "int", "max", "min", "abs", "torch"}
        if unknown:
            raise ConversionError("unbound-guard-symbol", f"{expression}: {sorted(unknown)}")
    lines = [f"def _check_shape_guards({', '.join(symbols)}):"]
    lines.append(
        '    """Shape guards Dynamo and Inductor recorded while compiling this substrate."""'
    )
    for symbol in symbols:
        lower, upper = guards.get("symbol_ranges", {}).get(symbol) or [None, None]
        if lower is not None and lower > 0:
            lines.append(f"    if not ({symbol} >= {int(lower)}):")
            lines.append(
                f"        raise SubstrateRefusal('size {symbol} below the compiled range "
                f"(>= {int(lower)})')"
            )
        if upper is not None:
            lines.append(f"    if not ({symbol} <= {int(upper)}):")
            lines.append(
                f"        raise SubstrateRefusal('size {symbol} above the compiled range "
                f"(<= {int(upper)})')"
            )
    for expression in expressions:
        lines.append(f"    if not ({expression}):")
        lines.append(f"        raise SubstrateRefusal({('shape guard failed: ' + expression)!r})")
    lines.append("    return None")
    return "\n".join(lines) + "\n", symbols


# --- assembly --------------------------------------------------------------------


def convert_record(record: dict[str, Any]) -> ConvertedSubstrate:
    """Convert one codegen record; raises :class:`ConversionError` when unfaithful."""
    problem_id = record["problem_id"]
    level, _, _ = parse_problem_id(problem_id)
    substrate_id = substrate_id_for(problem_id)

    eager = record.get("eager_output", {})
    if eager.get("kind") not in ("tensor", "tuple", "list"):
        raise ConversionError("unsupported-output", str(eager))
    if eager.get("count") != record.get("graph_outputs"):
        raise ConversionError("output-count-mismatch", f"{eager} vs {record.get('graph_outputs')}")
    meta = record.get("fw_metadata", {})
    if not meta.get("available"):
        raise ConversionError("no-aot-metadata")
    if any(kind != "non_alias" for kind in meta.get("output_types", [])):
        raise ConversionError("aliased-output", str(meta.get("output_types")))
    if meta.get("mutated_inp_runtime_indices"):
        raise ConversionError("runtime-input-mutation", str(meta["mutated_inp_runtime_indices"]))
    if (
        meta.get("num_intermediate_bases")
        or meta.get("is_rng_op_functionalized")
        or meta.get("num_outputs_rng_offset")
    ):
        raise ConversionError("aot-runtime-epilogue", json.dumps(meta, sort_keys=True))
    if not record.get("kernels"):
        raise ConversionError("no-triton-kernel")

    reference_text, forward = reference_model_source(record["problem_source"])
    signature_text, forward_args = forward_signature(forward)

    configs: dict[str, dict[str, Any]] = {}
    config_rules: dict[str, str] = {}
    kernel_blocks: list[str] = []
    kernel_imports: list[str] = []
    helper_texts: dict[str, str] = {}
    for kernel in record["kernels"]:
        config, rule = _choose_config(kernel)
        configs[kernel["name"]] = config
        config_rules[kernel["name"]] = rule
        imports, text, helpers = _kernel_text(kernel)
        for line in _normalise_kernel_imports(imports):
            if line not in kernel_imports:
                kernel_imports.append(line)
        for helper_name, helper_text in helpers.items():
            if helper_texts.get(helper_name, helper_text) != helper_text:
                raise ConversionError("helper-name-collision", helper_name)
            if helper_name not in helper_texts:
                helper_texts[helper_name] = helper_text
                kernel_blocks.append(helper_text)
        grid_text = _grid_function(kernel, config)
        kernel_blocks.append(text + ("\n\n" + grid_text if grid_text else ""))

    call_text, call_info = _rewrite_call(record, configs)
    call_tree = ast.parse(call_text)
    needed = _used_names(call_tree)
    prelude_kept: list[str] = []
    for node in _prelude_statements(record["output_code"]):
        names = _bound_names(node)
        if not names or set(names) & _DROPPED_PRELUDE_NAMES:
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "torch._inductor.async_compile":
            continue
        if set(names) & needed:
            prelude_kept.append(ast.unparse(node))
    defined = set()
    for line in prelude_kept + kernel_imports:
        defined |= set(_bound_names(ast.parse(line).body[0]))
    defined |= {kernel["name"] for kernel in record["kernels"]}
    defined |= {
        f"_grid_{kernel['name']}"
        for kernel in record["kernels"]
        if kernel["grid"]["type"] != "FixedGrid"
    }
    local = {
        n.id
        for n in ast.walk(call_tree)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
    }
    local |= {"args", "device_index"}
    builtins = {
        "len",
        "range",
        "int",
        "float",
        "max",
        "min",
        "tuple",
        "list",
        "isinstance",
        "print",
    }
    unresolved = sorted(needed - defined - local - builtins - {"torch", "triton", "math"})
    if unresolved:
        raise ConversionError("unresolved-name", ", ".join(unresolved))

    guard_text, guard_symbols = _guard_function(record.get("guards", {}))
    symbol_sources = record.get("guards", {}).get("symbol_sources", {})

    placeholders = record["placeholders"]
    tensor_checks: list[str] = []
    for placeholder in placeholders:
        if not placeholder["source"].startswith("L["):
            raise ConversionError("unsupported-placeholder-source", placeholder["source"])
        if placeholder["kind"] == "tensor":
            tensor_checks.append(
                f"        _check_tensor({placeholder['source']}, torch.{placeholder['dtype']}, "
                f"{placeholder['ndim']}, {placeholder['source']!r})"
            )
        elif placeholder["kind"] not in ("int", "float"):
            raise ConversionError("unsupported-placeholder-kind", placeholder["kind"])
    first_tensor = next((p for p in placeholders if p["kind"] == "tensor"), None)
    if first_tensor is None:
        raise ConversionError("no-tensor-input")

    modules = record.get("module_types", [])
    training_guard = sorted({m for m in modules if m in TRAINING_DEPENDENT_MODULES})

    scalar_guards: list[str] = []
    mapping = ", ".join([f'"{name}": {name}' for name in forward_args] + ['"self": self'])
    forward_lines = [
        f"    def forward({signature_text}):",
        '        """Bind the Dynamo graph inputs from their guard sources and run the wrapper."""',
        f"        L = {{{mapping}}}",
    ]
    for index, value in enumerate(record.get("inputs", [])):
        if value.get("kind") == "tensor" or index >= len(forward_args):
            continue
        name = forward_args[index]
        constant = value.get("value")
        if not isinstance(constant, int | float) or isinstance(constant, bool):
            raise ConversionError("unsupported-scalar-input", f"{name}={constant!r}")
        forward_lines += [
            f"        if L[{name!r}] != {constant!r}:",
            f"            raise SubstrateRefusal('scalar input {name} differs from the compiled "
            f"constant {constant!r}')",
        ]
        scalar_guards.append(name)
    if training_guard:
        forward_lines += [
            "        if not self.training:",
            "            raise SubstrateRefusal('compiled in training mode; eval mode differs for "
            + ", ".join(training_guard)
            + "')",
        ]
    forward_lines += tensor_checks
    if guard_symbols:
        bindings = ", ".join(f"{symbol}={symbol_sources[symbol]}" for symbol in guard_symbols)
        forward_lines.append(f"        _check_shape_guards({bindings})")
    forward_lines.append("        args = [" + ", ".join(p["source"] for p in placeholders) + "]")
    forward_lines.append(f"        outputs = call(args, {first_tensor['source']}.device.index)")
    if eager["kind"] == "tensor":
        forward_lines.append("        return outputs[0]")
    else:
        forward_lines.append(f"        return {eager['kind']}(outputs)")

    versions = record.get("versions", {})
    settings = record.get("settings", {})
    header = textwrap.dedent(
        f'''\
        """Q1 S1 substrate {substrate_id}: TorchInductor Triton for KernelBench {problem_id}.

        Compiler-generated (not model-generated) code. Generated by torch {versions.get("torch")}
        (git {versions.get("torch_git")}) with Triton {versions.get("triton")}, codegen mode
        {record.get("mode")}, settings {json.dumps(settings, sort_keys=True)}.
        Problem: KernelBench@{KERNELBENCH_PROBLEMS_REVISION} {record.get("problem_path")} (MIT).
        Kernels: TorchInductor output (PyTorch, BSD-3-Clause), heuristic decorators removed and
        launches rewritten to plain ``kernel[grid](...)`` JIT launches by
        harness/q1/substrates/inductor_convert.py ({CONVERTER_VERSION}). Inputs outside the
        compiled specialisation raise SubstrateRefusal before any launch.
        """
        '''
    )
    parts = [
        header,
        "import torch",
        "import triton",
        "import triton.language as tl",
        *[
            line
            for line in kernel_imports
            if line not in ("import triton", "import triton.language as tl")
        ],
        *prelude_kept,
        "",
        "",
        "# --- Reference Model from KernelBench (MIT), docstrings dropped; ModelNew inherits it",
        reference_text,
        "",
        "# --- TorchInductor kernels (only the Inductor heuristic decorator removed) ---",
        "",
        "\n\n".join(kernel_blocks),
        "",
        "# --- TorchInductor host wrapper; launches rewritten to plain JIT ---",
        "",
        call_text,
        "",
        "class SubstrateRefusal(ValueError):",
        '    """Raised before any launch when an input is outside the compiled specialisation."""',
        "",
        "",
        "def _check_tensor(value, dtype, ndim, source):",
        "    if not isinstance(value, torch.Tensor):",
        "        raise SubstrateRefusal(f'{source} is not a tensor')",
        "    if value.dtype != dtype or value.dim() != ndim or value.device.type != 'cuda':",
        "        raise SubstrateRefusal(",
        "            f'{source}: expected cuda {dtype} rank {ndim}, got {value.device.type} '",
        "            f'{value.dtype} rank {value.dim()}'",
        "        )",
        "    return None",
        "",
        "",
        guard_text,
        "",
        "class ModelNew(Model):",
        f'    """TorchInductor substrate for {problem_id}; same constructor as Model."""',
        "",
        *forward_lines,
        "",
    ]
    kernel_py = "\n".join(parts)
    try:
        compile(kernel_py, "kernel.py", "exec")
    except SyntaxError as exc:  # pragma: no cover - would be a converter bug
        raise ConversionError("generated-syntax-error", str(exc)) from exc

    original = record["output_code"]
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            kernel_py.splitlines(keepends=True),
            fromfile="inductor_output.py",
            tofile="kernel.py",
        )
    )
    diff_sha = sha256_text(diff)
    pytorch = SOURCES["pytorch"]
    if versions.get("torch_git") and versions["torch_git"] != pytorch.revision:
        raise ConversionError("torch-revision-mismatch", versions["torch_git"])
    kernel_names = [kernel["name"] for kernel in record["kernels"]]
    transformations = [
        {
            "name": "inductor-codegen",
            "detail": f"torch.compile(dynamic=True, fullgraph=True) under no_grad, mode "
            f"{record.get('mode')}; Inductor deterministic=True, triton.autotune_pointwise="
            "False, caches disabled, duck sizing off"
            + (
                f"; GEMM templates via max_autotune TRITON ({record.get('gemm_choice_rule')})"
                if settings.get("max_autotune")
                else ""
            ),
        },
        {
            "name": "strip-triton-heuristics",
            "detail": "removed the @triton_heuristics decorator from "
            + ", ".join(kernel_names)
            + "; configs: "
            + "; ".join(f"{name}={config_rules[name]}" for name in kernel_names),
        },
        {
            "name": "plain-jit-launch",
            "detail": "kernel.run(..., stream=s) -> kernel[grid](..., config kwargs, num_warps, "
            "num_stages, debug, sanitize_overflow=False) with Inductor's compile options",
        },
        {
            "name": "inductor-gridexpr-grid",
            "detail": "grid functions from Inductor GridExpr ("
            + ", ".join(sorted({k["grid"]["type"] for k in record["kernels"]}))
            + ") with ceil division written as triton.cdiv; a FixedGrid template keeps the "
            "grid Inductor passed as trailing launcher arguments",
        },
        {
            "name": "device-index-from-inputs",
            "detail": "_DeviceGuard(0)/set_device(0) -> the first tensor input's device; "
            "get_raw_stream lookups removed",
        },
        {
            "name": "guards-as-refusals",
            "detail": f"{len(record.get('guards', {}).get('expressions', []))} shape guards and "
            f"{len(tensor_checks)} tensor dtype/rank/device checks raise SubstrateRefusal "
            "before any launch"
            + (f"; training-mode guard for {', '.join(training_guard)}" if training_guard else "")
            + (
                f"; scalar inputs pinned to native values: {', '.join(scalar_guards)}"
                if scalar_guards
                else ""
            ),
        },
        {
            "name": "modelnew-wrapper",
            "detail": "embedded reference Model (KernelBench, MIT) via ast.unparse without "
            "get_inputs/get_init_inputs, comments or docstrings; ModelNew(Model) binds graph "
            "inputs from Dynamo guard sources",
        },
        {
            "name": "normalization-diff",
            "detail": "unified diff inductor_output.py -> kernel.py (normalization.diff)",
            "diff_sha256": diff_sha,
        },
    ]
    notes = (
        f"Compiled from KernelBench@{KERNELBENCH_PROBLEMS_REVISION} {record.get('problem_path')} "
        f"(MIT). Triton kernels: {len(kernel_names)}; library calls in the wrapper: "
        + (", ".join(call_info["library_calls"]) or "none")
        + ". Admission (hook visibility and gate a at native shapes) is decided on GPU, not here."
    )
    extra_files = {
        "inductor_output.py.txt": original,
        "normalization.diff": diff,
    }
    files_for_listing = {"kernel.py": kernel_py, **extra_files}
    build = {
        "converter_version": CONVERTER_VERSION,
        "codegen_record_version": record.get("record_version"),
        "problem_id": problem_id,
        "mode": record.get("mode"),
        "settings": settings,
        "gemm_choice_rule": record.get("gemm_choice_rule"),
        "device_properties": record.get("device_properties"),
        "mock_patches": record.get("mock_patches", []),
        "versions": versions,
        "inputs": record.get("inputs"),
        "input_draw": record.get("input_draw"),
        "placeholders": placeholders,
        "guards": record.get("guards"),
        "fw_metadata": meta,
        "module_types": modules,
        "training_guard": training_guard,
        "kernels": [
            {
                "name": kernel["name"],
                "heuristic": kernel.get("heuristic"),
                "heuristic_type": kernel.get("heuristic_type"),
                "size_hints": kernel.get("size_hints"),
                "config": configs[kernel["name"]],
                "config_rule": config_rules[kernel["name"]],
                "n_configs": len(kernel.get("configs", [])),
                "grid": kernel.get("grid"),
                "signature": kernel.get("signature"),
                "constants": kernel.get("constants"),
                "compile_options": kernel.get("compile_options"),
                "launch_count": call_info["launches"].get(kernel["name"], 0),
            }
            for kernel in record["kernels"]
        ],
        "library_calls": call_info["library_calls"],
        "triton_coverage": "triton-only" if not call_info["library_calls"] else "hybrid-library",
        "codegen_seconds": record.get("codegen_seconds"),
    }
    substrate = {
        "substrate_id": substrate_id,
        "problem_id": problem_id,
        "level": level,
        "kernelbench_revision": KERNELBENCH_PROBLEMS_REVISION,
        "source_kind": "inductor",
        "source_repo": pytorch.repo,
        "source_revision": pytorch.revision,
        "source_license": pytorch.license,
        "origin_path": "torch/_inductor/codegen/triton.py",
        "transformations": transformations,
        "notes": notes,
        "schema_version": SCHEMA_VERSION,
    }
    converted = ConvertedSubstrate(substrate_id, kernel_py, substrate, build, extra_files)
    listing = {**files_for_listing, "build.json": converted.files()["build.json"]}
    substrate["files"] = [
        {"path": path, "sha256": sha256_text(text)} for path, text in sorted(listing.items())
    ]
    validate_substrate(substrate)
    return converted
