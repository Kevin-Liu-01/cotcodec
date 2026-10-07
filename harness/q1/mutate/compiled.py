"""Compiled-specialization deduplication (the GPU-side TCE hook).

Two mutants are compile-equivalent when every Triton kernel they launch at the
substrate's native specialization compiles to the same cubin with line info
disabled, and their launch code is the same. Line info must be off
(``TRITON_DISABLE_LINE_INFO=1``): KernelBench loads candidates from random
temporary paths and Triton embeds source locations in the binary, so with
line info on, identical code never hashes equal.

The hook has two halves:

1. **Record** (needs a GPU; run once per *parent* substrate at admission):
   :func:`record_specializations` installs Triton's official
   ``knobs.runtime.jit_post_compile_hook`` and captures, for every kernel
   compiled during one native forward pass, Triton's own serialized
   specialization (signature, constexprs, divisibility attributes, options).
2. **Replay** (no GPU; run inside a GPU-less container): :func:`compile_hashes`
   imports a mutant's ``kernel.py`` and compiles each recorded kernel with
   ``triton.compile(ASTSource(...), target=GPUTarget("cuda", 90, 32))``. Triton
   3.6 compiles sm_90 cubins without a device; this was checked in a GPU-less
   container on fal-h100-01.

A kernel the parent never launched at its native specialization has no record;
mutations confined to it cannot change the forward result and are classified
``unlaunched`` (equivalent).

Run :func:`compile_hashes` only in a fresh subprocess inside a GPU-less
container (see ``python -m harness.q1.mutate.compiled``): it imports the
mutant module, which executes its top-level code.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import importlib.util
import json
import os
import signal
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.q1.mutate.source import KernelSource, is_jit_decorator, normalized_ast_dump

SPEC_SCHEMA = "q1-triton-specializations/1"
DEFAULT_TARGET = ("cuda", 90, 32)


class CompileHookError(RuntimeError):
    """The specialization record or the compile environment is invalid."""


@dataclass(frozen=True)
class Specialization:
    """One recorded compile of one jit function (Triton's serialized form)."""

    function: str
    specialization_data: str

    def to_json(self) -> dict[str, str]:
        return {"function": self.function, "specialization_data": self.specialization_data}


def launch_scope_hash(text: str) -> str:
    """Hash of the module with every jit function body blanked (launch semantics only)."""
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and any(
            is_jit_decorator(d) for d in node.decorator_list
        ):
            node.body = [ast.Pass()]
    return hashlib.sha256(normalized_ast_dump(tree).encode()).hexdigest()


def compiled_key(cubin_hashes: dict[str, list[str]], launch_hash: str) -> str:
    payload = json.dumps(
        {"cubins": {k: sorted(v) for k, v in sorted(cubin_hashes.items())}, "launch": launch_hash},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def load_specializations(path: Path) -> list[Specialization]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != SPEC_SCHEMA:
        raise CompileHookError(f"{path}: schema must be {SPEC_SCHEMA}")
    records = data.get("records")
    if not isinstance(records, list) or not records:
        raise CompileHookError(f"{path}: no specialization records")
    out = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"function", "specialization_data"}:
            raise CompileHookError(f"{path}: malformed record {record!r}")
        json.loads(record["specialization_data"])  # must be Triton's JSON
        out.append(Specialization(record["function"], record["specialization_data"]))
    return out


def dump_specializations(records: list[Specialization], triton_version: str) -> str:
    return json.dumps(
        {
            "schema": SPEC_SCHEMA,
            "triton_version": triton_version,
            "line_info_disabled": os.environ.get("TRITON_DISABLE_LINE_INFO") == "1",
            "records": [r.to_json() for r in records],
        },
        indent=1,
        sort_keys=True,
    )


@contextlib.contextmanager
def record_specializations() -> Iterator[list[Specialization]]:
    """Capture every Triton compile in the block (GPU side, parent substrates only).

    Usage, in the substrate-admission job::

        with record_specializations() as records:
            model(*native_inputs)
            torch.cuda.synchronize()
        Path("specializations.json").write_text(dump_specializations(records, triton.__version__))
    """
    from triton import knobs  # imported lazily: never needed for enumeration

    records: list[Specialization] = []
    previous = knobs.runtime.jit_post_compile_hook

    def hook(
        *,
        key: Any,
        repr: str,
        fn: Any,
        compile: dict,
        is_manual_warmup: bool,
        already_compiled: bool,
    ) -> None:
        records.append(Specialization(fn.name.rsplit(".", 1)[-1], compile["specialization_data"]))
        if previous is not None:
            previous(
                key=key,
                repr=repr,
                fn=fn,
                compile=compile,
                is_manual_warmup=is_manual_warmup,
                already_compiled=already_compiled,
            )

    knobs.runtime.jit_post_compile_hook = hook
    try:
        yield records
    finally:
        knobs.runtime.jit_post_compile_hook = previous


@contextlib.contextmanager
def _compiled_mode() -> Iterator[None]:
    """Hide ``TRITON_INTERPRET`` while kernels are decorated: dedup compiles, never interprets.

    ``triton.jit`` returns an interpreter wrapper instead of a ``JITFunction``
    when ``TRITON_INTERPRET=1`` is set at decoration time (for example by a CPU
    test elsewhere in the same process), which would make every recorded
    function look missing.
    """
    saved = os.environ.pop("TRITON_INTERPRET", None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ["TRITON_INTERPRET"] = saved


def _import_module(path: Path) -> Any:
    name = "q1_compile_" + hashlib.sha256(str(path).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CompileHookError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    with _compiled_mode():
        spec.loader.exec_module(module)
    return module


def _deserialize(spec: Specialization) -> tuple[dict, dict, dict, dict]:
    """Mirror of ``JITFunction.preload`` without a device (Triton 3.6 format)."""
    import triton.language as tl
    from triton.runtime.jit import convert_to_tuple_if_list

    obj = json.loads(spec.specialization_data)
    constexprs = {}
    for key, value in zip(obj["constant_keys"], obj["constant_vals"], strict=True):
        if tl.dtype.is_dtype(value):
            value = tl.dtype(value)
        elif isinstance(value, dict) and "constexpr" in value:
            value = tl.constexpr(value["constexpr"])
        constexprs[tuple(key)] = value
    attrs = {tuple(k): v for k, v in zip(obj["attrs_keys"], obj["attrs_vals"], strict=True)}
    signature = {k: convert_to_tuple_if_list(v) for k, v in obj["signature"].items()}
    options = {k: tuple(v) if isinstance(v, list) else v for k, v in obj["options"].items()}
    return signature, constexprs, attrs, options


def compile_hashes(
    kernel_py: Path, records: list[Specialization], target: tuple[str, int, int] = DEFAULT_TARGET
) -> dict[str, list[str]]:
    """sha256 of the cubin of every recorded specialization, compiled from ``kernel_py``.

    Raises ``CompileHookError`` if line info is enabled or a recorded function
    is missing; any Triton compile error propagates (the caller records the
    mutant as compile-fail).
    """
    if os.environ.get("TRITON_DISABLE_LINE_INFO") != "1":
        raise CompileHookError("TRITON_DISABLE_LINE_INFO=1 is required for compiled dedup")
    import triton
    from triton.backends.compiler import GPUTarget
    from triton.compiler import ASTSource
    from triton.runtime.jit import JITFunction

    module = _import_module(Path(kernel_py))
    hashes: dict[str, list[str]] = {}
    for record in records:
        fn = getattr(module, record.function, None)
        while fn is not None and not isinstance(fn, JITFunction) and hasattr(fn, "fn"):
            fn = fn.fn  # unwrap Autotuner / Heuristics to the JITFunction
        if not isinstance(fn, JITFunction):
            raise CompileHookError(f"{kernel_py}: no jit function {record.function}")
        signature, constexprs, attrs, options = _deserialize(record)
        compiled = triton.compile(
            ASTSource(fn, signature, constexprs, attrs), target=GPUTarget(*target), options=options
        )
        cubin = compiled.asm["cubin"]
        hashes.setdefault(record.function, []).append(hashlib.sha256(cubin).hexdigest())
    return hashes


def classify(
    parent_key: str,
    mutant_text: str,
    mutant_hashes: dict[str, list[str]] | None,
    seen: dict[str, str],
    mutant_id: str,
) -> tuple[str, str | None]:
    """Return (status, compiled_key) for one mutant.

    status: ``compile-fail`` | ``equivalent-to-parent`` | ``duplicate`` | ``distinct``.
    """
    if mutant_hashes is None:
        return "compile-fail", None
    key = compiled_key(mutant_hashes, launch_scope_hash(mutant_text))
    if key == parent_key:
        return "equivalent-to-parent", key
    if key in seen:
        return "duplicate", key
    seen[key] = mutant_id
    return "distinct", key


def main(argv: list[str] | None = None) -> int:
    """Compile a batch of kernel files against one specialization record.

    Input: ``--spec specializations.json`` and ``--kernels`` paths. Output: one
    JSON line per kernel ``{"kernel": path, "hashes": {...}}`` or
    ``{"kernel": path, "error": "..."}``. Run in a GPU-less container.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--kernels", type=Path, nargs="+", required=True)
    parser.add_argument("--per-kernel-timeout-s", type=int, default=600)
    args = parser.parse_args(argv)
    os.environ.setdefault("TRITON_DISABLE_LINE_INFO", "1")
    os.environ.setdefault("TRITON_CACHE_DIR", tempfile.mkdtemp(prefix="q1-triton-cache-"))
    os.environ.pop("TRITON_INTERPRET", None)  # compile for sm_90, never interpret
    records = load_specializations(args.spec)

    def on_alarm(signum: int, frame: Any) -> None:
        raise TimeoutError(f"compile exceeded {args.per_kernel_timeout_s} s")

    previous = signal.signal(signal.SIGALRM, on_alarm)
    try:
        for kernel in args.kernels:
            signal.alarm(args.per_kernel_timeout_s)
            try:
                KernelSource(kernel.read_text(encoding="utf-8"))
                row = {"kernel": str(kernel), "hashes": compile_hashes(kernel, records)}
            except TimeoutError as exc:
                row = {"kernel": str(kernel), "error": f"timeout: {exc}"}
            except Exception as exc:  # noqa: BLE001 - reported per kernel
                row = {"kernel": str(kernel), "error": f"{type(exc).__name__}: {exc}"[:2000]}
            finally:
                signal.alarm(0)
            print(json.dumps(row, sort_keys=True), flush=True)
    finally:
        signal.signal(signal.SIGALRM, previous)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
