"""S2 substrates: human-written pre-2025 Triton kernels mapped to KernelBench problems.

Sources (licences read from each repository's LICENSE at the pinned revision):

- FlagGems tag v1.0-manual @18b8e428 (Apache-2.0, copyright 2024 BAAI);
- Liger-Kernel tag v0.3.1 @1520999e (BSD-2-Clause, copyright 2024 LinkedIn; several
  files state that they incorporate Unsloth code under Apache-2.0);
- Triton python/tutorials @105cb564 (MIT, copyright 2018-2020 Philippe Tillet,
  2020-2022 OpenAI).

Each entry names one upstream file (sha256-pinned), the KernelBench problem it
implements, the normalisations applied, and a short ``ModelNew.forward`` that
calls the upstream host function. FlagGems and Liger files are kept whole (their
backward kernels included, listed as non-forward); tutorial files are scripts, so
only their kernels (and the matmul host function) are extracted.

Normalisations are mechanical text edits, each recorded with its detail, and the
unified diff from the upstream text to the substrate is stored per substrate:

``strip-libentry``          remove ``@libentry()`` and its import (FlagGems caches the
                            compiled kernel and relaunches it directly, bypassing the
                            launch hook);
``drop-debug-prints``       remove ``if __debug__: print("GEMS ...")`` blocks;
``pin-autotune``            ``configs=X`` -> ``configs=(X)[i:i + 1]``: one config, the first
                            listed one that compiles for sm_90 at fp32 (``i`` recorded),
                            so every gate and the audit run the same program;
``tl-math-to-libdevice``    ``tl.math.tanh``/``tl.math.pow`` (absent in Triton 3.6) ->
                            ``libdevice.tanh``/``libdevice.pow``;
``liger-inline-utils``      inline ``ensure_contiguous`` and ``calculate_settings`` from
                            ``liger_kernel/ops/utils.py`` and resolve the Triton-version
                            import of ``rsqrt`` to its Triton >= 3 branch;
``tutorial-*``              entry-specific edits to tutorial host code, listed per entry.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import re
import textwrap
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harness.q1.schema import (
    KERNELBENCH_PROBLEMS_REVISION,
    SCHEMA_VERSION,
    parse_problem_id,
    validate_substrate,
)
from harness.q1.substrates.inductor_convert import (
    _strip_docstrings,
    forward_signature,
    sha256_text,
)
from harness.q1.substrates.sources import SOURCES, VENDORED_SOURCES_ROOT, problem_file

S2_BUILD_VERSION = "q1-s2-build/1"

#: Upstream files, by (source key, path): (size in bytes, sha256). Measured on the
#: host clones at the pinned revisions on 2026-10-07.
UPSTREAM_FILES: dict[tuple[str, str], tuple[int, str]] = {
    ("flaggems", "LICENSE"): (
        10218,
        "aab2b520bd1336cc55cc9eb10602e1086c100e6f6eb3ce725797d6900ad7ad9e",
    ),
    ("flaggems", "src/flag_gems/relu.py"): (
        3663,
        "84d41bce42f21dc027e3283179327f8f2c8a22632b0b7cb7f8d7f5349f0f0661",
    ),
    ("flaggems", "src/flag_gems/gelu.py"): (
        3225,
        "1c22f86d9aebe6df4a647f30f83282f0fbb3c07dcf6e870c92785825add95d5f",
    ),
    ("flaggems", "src/flag_gems/silu.py"): (
        3902,
        "ea539f8459b783da98c8dd0727283c10adb202c633d8e6fb5951e62714ff8e03",
    ),
    ("flaggems", "src/flag_gems/softmax.py"): (
        4816,
        "5992370739fc20209edaac3f58949a9443c317c5dd45898965b4de5ca08d96e2",
    ),
    ("flaggems", "src/flag_gems/layernorm.py"): (
        8774,
        "6cd7ebdac4123db22920a553d6febf1a7ca04e7812642704de8ffea2a2fe5313",
    ),
    ("flaggems", "src/flag_gems/cumsum.py"): (
        1879,
        "69bf8028bb91b095e493c738a43f2588e85bc7ef1b1db4452fa5e4529f0a0060",
    ),
    ("flaggems", "src/flag_gems/mm.py"): (
        6958,
        "acbbafe673855558e4bcec0eadaee5533fc6a1f3e3afd627d54f2fc9bf95e675",
    ),
    ("flaggems", "src/flag_gems/bmm.py"): (
        5385,
        "5f13f155e1da5734872dce1d467913a6326ce8ca97a12caba09219a9298dabee",
    ),
    ("flaggems", "src/flag_gems/mul.py"): (
        3935,
        "b9d9f283ecc83f1f91d097d097b535ce9879b2eb39434e77e7147f0793645ff0",
    ),
    ("flaggems", "src/flag_gems/triu.py"): (
        3223,
        "376d856ba4075e7aa56c2d16f201a511a514f98de7d384fd55df5fe9c0dd492c",
    ),
    ("liger", "LICENSE"): (
        1312,
        "3a1ccb0c7274b68e1af2ca1d54b10b662085ca56753400182ecf87ae33f2d1a8",
    ),
    ("liger", "NOTICE"): (173, "05791763d696bc4cbfecc001e7bcc3bb5cfcb8c613d62d65f41e84a47b816bcb"),
    ("liger", "src/liger_kernel/ops/utils.py"): (
        1941,
        "639b1b46e655a2cc2c3332134d38858084c937640ed0ae0c7000149dc1375271",
    ),
    ("liger", "src/liger_kernel/ops/rms_norm.py"): (
        9921,
        "e26884a0349db1cd06ba1237069051c6dea289e15070dd909cda78a3c3d507df",
    ),
    ("liger", "src/liger_kernel/ops/layer_norm.py"): (
        7422,
        "ba718c60c38faad90cf5a4eba2485caa03e6b15d8050ded8ceff3a8ac541f4e2",
    ),
    ("liger", "src/liger_kernel/ops/cross_entropy.py"): (
        12317,
        "eaea0f49c2a95c9ee074194ea529d9710e5f41ee76247623515b2bfc17f89021",
    ),
    ("liger", "src/liger_kernel/ops/kl_div.py"): (
        8342,
        "aa79ad150c2e3b7151ecebeea7f0c3ce9903d40d4ba7039a5a570ee8af72b079",
    ),
    ("triton-tutorials", "LICENSE"): (
        1132,
        "92640fb97222fd0a698ff28ce0c3782c172623f8d6c609b557636a80f28fb946",
    ),
    ("triton-tutorials", "python/tutorials/02-fused-softmax.py"): (
        9966,
        "4608d6fa6424af757cb876fe04908d40501a9afc2ac281dafaa233fc60eab360",
    ),
    ("triton-tutorials", "python/tutorials/03-matrix-multiplication.py"): (
        19473,
        "9cbb07652b3d5cf07184fc54db62a36dae47cf35274e25d517b770ab7ee3d767",
    ),
    ("triton-tutorials", "python/tutorials/05-layer-norm.py"): (
        15809,
        "c8233db83a56549a5e81af4b4b64cd045130796aced1f9d86d3277816a613341",
    ),
}

#: Directory names of the source checkouts under ``--sources-root``.
SOURCE_DIRS = {
    "flaggems": "FlagGems",
    "liger": "Liger-Kernel",
    "triton-tutorials": "triton-tutorials",
}

#: Triton 3.6 lacks these ``tl.math`` functions; libdevice has them.
TL_MATH_MISSING_IN_TRITON_36 = ("tanh", "pow")


class S2BuildError(ValueError):
    """An S2 entry cannot be built as specified."""


@dataclass(frozen=True)
class S2Entry:
    key: str
    source: str
    path: str
    problem_id: str
    forward_body: str
    forward_kernels: tuple[str, ...]
    mode: str = "file"  # "file" keeps the normalised file; "names" extracts top-level defs
    names: tuple[str, ...] = ()
    autotune_index: dict[str, int] = field(default_factory=dict)
    edits: tuple[str, ...] = ()
    notes: str = ""

    @property
    def substrate_id(self) -> str:
        level, number, name = parse_problem_id(self.problem_id)
        return f"s2-{self.key}-L{level}-{number}_{name}"

    @property
    def kernel_family(self) -> str:
        """Upstream kernel identity (file and forward kernels), for clustering substrates."""
        return f"{self.source}:{self.path}:{','.join(self.forward_kernels)}"


# --- text transformations -------------------------------------------------------


def _replace_once(text: str, old: str, new: str, what: str) -> str:
    if text.count(old) != 1:
        raise S2BuildError(f"{what}: expected exactly one {old!r}, found {text.count(old)}")
    return text.replace(old, new)


def strip_libentry(text: str) -> tuple[str, str]:
    lines = text.splitlines(keepends=True)
    kept = [
        line
        for line in lines
        if line.strip() not in ("@libentry()", "from .__libentry__ import libentry")
    ]
    removed = len(lines) - len(kept)
    if removed == 0:
        raise S2BuildError("strip-libentry: nothing to strip")
    return "".join(kept), f"removed {removed} libentry lines (decorators and import)"


_DEBUG_PRINT = re.compile(
    r"^(?P<indent>[ \t]*)if __debug__:\n(?P=indent)[ \t]+print\([^\n]*\)\n", re.MULTILINE
)


def drop_debug_prints(text: str) -> tuple[str, str]:
    new, count = _DEBUG_PRINT.subn("", text)
    if count == 0:
        raise S2BuildError("drop-debug-prints: no debug print block")
    return new, f"removed {count} 'if __debug__: print(...)' blocks"


def pin_autotune(text: str, indices: dict[str, int]) -> tuple[str, str]:
    """``configs=X`` -> ``configs=(X)[i:i + 1]`` on every ``@triton.autotune`` decorator."""
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    edits: list[tuple[int, int, str]] = []
    pinned = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not (
                isinstance(decorator, ast.Call)
                and ast.unparse(decorator.func) in ("triton.autotune", "autotune")
            ):
                continue
            keyword = next((k for k in decorator.keywords if k.arg == "configs"), None)
            if keyword is None:
                raise S2BuildError(f"pin-autotune: {node.name} has no configs= keyword")
            value = keyword.value
            start = offsets[value.lineno - 1] + value.col_offset
            end = offsets[value.end_lineno - 1] + value.end_col_offset
            index = indices.get(node.name, 0)
            original = text[start:end]
            edits.append((start, end, f"({original})[{index}:{index + 1}]"))
            pinned.append(f"{node.name}[{index}]")
    if not edits:
        raise S2BuildError("pin-autotune: no @triton.autotune decorator")
    unknown = set(indices) - {item.split("[")[0] for item in pinned}
    if unknown:
        raise S2BuildError(f"pin-autotune: indices for unknown kernels {sorted(unknown)}")
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text, "pinned autotune configs (kernel[index]): " + ", ".join(pinned)


def tl_math_to_libdevice(text: str) -> tuple[str, str]:
    count = 0
    for name in TL_MATH_MISSING_IN_TRITON_36:
        pattern = f"tl.math.{name}("
        count += text.count(pattern)
        text = text.replace(pattern, f"libdevice.{name}(")
    if count == 0:
        raise S2BuildError("tl-math-to-libdevice: no tl.math.tanh/pow call")
    text = _replace_once(
        text,
        "import triton.language as tl\n",
        "import triton.language as tl\nfrom triton.language.extra import libdevice\n",
        "tl-math-to-libdevice",
    )
    return text, f"{count} tl.math.tanh/pow calls -> triton.language.extra.libdevice"


def liger_inline_utils(text: str, utils_text: str) -> tuple[str, str]:
    utils = ast.parse(utils_text)
    wanted = ("ensure_contiguous", "calculate_settings")
    lines = utils_text.splitlines(keepends=True)
    blocks = []
    for node in utils.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            blocks.append("".join(lines[start - 1 : node.end_lineno]))
    if len(blocks) != len(wanted):
        raise S2BuildError("liger-inline-utils: helpers not found in utils.py")
    tree = ast.parse(text)
    src_lines = text.splitlines(keepends=True)
    replaced = []
    for node in reversed(tree.body):
        segment = None
        if isinstance(node, ast.ImportFrom) and node.module == "liger_kernel.ops.utils":
            imported = {alias.name for alias in node.names}
            if not imported <= set(wanted) | {"compare_version"}:
                raise S2BuildError(f"liger-inline-utils: unexpected utils imports {imported}")
            segment = "import functools\n\n\n" + "\n\n".join(b.rstrip() + "\n" for b in blocks)
            replaced.append("utils import")
        elif isinstance(node, ast.If) and "compare_version" in ast.unparse(node.test):
            segment = "from triton.language.extra.libdevice import rsqrt\n"
            replaced.append("triton-version rsqrt import")
        if segment is not None:
            src_lines[node.lineno - 1 : node.end_lineno] = [segment]
    if not replaced:
        raise S2BuildError("liger-inline-utils: no utils import")
    return "".join(src_lines), (
        "inlined ensure_contiguous and calculate_settings from "
        "liger_kernel/ops/utils.py@v0.3.1; replaced: " + ", ".join(reversed(replaced))
    )


def extract_names(text: str, names: tuple[str, ...]) -> tuple[str, str]:
    """Keep the module imports plus the named top-level definitions, in file order."""
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    kept = []
    found = set()
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            kept.append("".join(lines[node.lineno - 1 : node.end_lineno]))
        elif isinstance(node, ast.FunctionDef | ast.ClassDef) and node.name in names:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            kept.append("\n\n" + "".join(lines[start - 1 : node.end_lineno]))
            found.add(node.name)
    missing = set(names) - found
    if missing:
        raise S2BuildError(f"extract-names: {sorted(missing)} not in file")
    imports = [k for k in kept if not k.startswith("\n\n")]
    if any("driver" in k for k in imports):
        imports = [k for k in imports if "driver" not in k]
    defs = [k for k in kept if k.startswith("\n\n")]
    return "".join(imports) + "".join(defs).rstrip() + "\n", (
        "kept imports and " + ", ".join(names) + "; dropped the tutorial script around them"
    )


def tutorial_edit(old: str, new: str, label: str) -> Callable[[str], tuple[str, str]]:
    def edit(text: str) -> tuple[str, str]:
        return _replace_once(text, old, new, label), f"{old.strip()!r} -> {new.strip()!r}"

    edit.__name__ = label
    return edit


TUTORIAL_EDITS: dict[str, Callable[[str], tuple[str, str]]] = {
    "tutorial-matmul-store-dtype": tutorial_edit(
        "c = accumulator.to(tl.float16)",
        "c = accumulator.to(c_ptr.dtype.element_ty)",
        "tutorial-matmul-store-dtype",
    ),
    "tutorial-matmul-output-dtype": tutorial_edit(
        "dtype=torch.float16)", "dtype=a.dtype)", "tutorial-matmul-output-dtype"
    ),
    "tutorial-matmul-cuda-configs": tutorial_edit(
        "configs=get_autotune_config()",
        "configs=get_cuda_autotune_config()",
        "tutorial-matmul-cuda-configs",
    ),
}


# --- catalog ------------------------------------------------------------------------

_FG = "flaggems"
_LG = "liger"
_TT = "triton-tutorials"
FILE_EDITS_FG = ("strip-libentry", "drop-debug-prints", "pin-autotune")

CATALOG: tuple[S2Entry, ...] = (
    S2Entry(
        "flaggems-relu",
        _FG,
        "src/flag_gems/relu.py",
        "L1/19_ReLU",
        "return relu(x)",
        ("relu_forward_kernel",),
        edits=FILE_EDITS_FG,
        notes="Block pointers without boundary_check: a size that is not a multiple of "
        "the block reads and writes past the end (expected natural fault off-native).",
    ),
    S2Entry(
        "flaggems-gelu",
        _FG,
        "src/flag_gems/gelu.py",
        "L1/26_GELU_",
        "return gelu(x)",
        ("gelu_none_kernel",),
        edits=(*FILE_EDITS_FG, "tl-math-to-libdevice"),
    ),
    S2Entry(
        "flaggems-gelu-tanh",
        _FG,
        "src/flag_gems/gelu.py",
        "L1/88_MinGPTNewGelu",
        'return gelu(x, approximate="tanh")',
        ("gelu_tanh_kernel",),
        edits=(*FILE_EDITS_FG, "tl-math-to-libdevice"),
        notes="Upstream constant 0.79788456 for sqrt(2/pi).",
    ),
    S2Entry(
        "flaggems-silu",
        _FG,
        "src/flag_gems/silu.py",
        "L1/25_Swish",
        "return silu(x)",
        ("silu_forward_kernel",),
        edits=FILE_EDITS_FG,
    ),
    S2Entry(
        "flaggems-softmax",
        _FG,
        "src/flag_gems/softmax.py",
        "L1/23_Softmax",
        "return softmax(x, dim=1)",
        ("softmax_kernel",),
        edits=FILE_EDITS_FG,
        notes="BLOCK_N = next_power_of_2(N): one row per block at N = 393,216.",
    ),
    S2Entry(
        "flaggems-layernorm",
        _FG,
        "src/flag_gems/layernorm.py",
        "L1/40_LayerNorm",
        "return layer_norm(x, self.ln.normalized_shape, self.ln.weight, self.ln.bias, "
        "self.ln.eps)[0]",
        ("layer_norm_kernel",),
        edits=FILE_EDITS_FG,
    ),
    S2Entry(
        "flaggems-cumsum",
        _FG,
        "src/flag_gems/cumsum.py",
        "L1/89_cumsum",
        "return cumsum(x, dim=self.dim)",
        ("cumsum_kernel",),
        edits=FILE_EDITS_FG,
    ),
    *(
        S2Entry(
            "flaggems-mm",
            _FG,
            "src/flag_gems/mm.py",
            problem,
            "return mm(A, B)",
            ("mm_kernel",),
            edits=FILE_EDITS_FG,
        )
        for problem in (
            "L1/1_Square_matrix_multiplication_",
            "L1/2_Standard_matrix_multiplication_",
            "L1/6_Matmul_with_large_K_dimension_",
            "L1/7_Matmul_with_small_K_dimension_",
            "L1/8_Matmul_with_irregular_shapes_",
            "L1/9_Tall_skinny_matrix_multiplication_",
        )
    ),
    S2Entry(
        "flaggems-bmm",
        _FG,
        "src/flag_gems/bmm.py",
        "L1/3_Batched_matrix_multiplication",
        "return bmm(A, B)",
        ("bmm_kernel",),
        edits=FILE_EDITS_FG,
    ),
    S2Entry(
        "flaggems-mul-scalar",
        _FG,
        "src/flag_gems/mul.py",
        "L1/5_Matrix_scalar_multiplication",
        "return mul(A, s)",
        ("mul_scalar_kernel",),
        edits=FILE_EDITS_FG,
        notes="Upstream mul() keeps a try/except around broadcast_tensors (tensor-tensor "
        "branch); KernelBench's static checker treats try/except as strict.",
    ),
    S2Entry(
        "flaggems-triu",
        _FG,
        "src/flag_gems/triu.py",
        "L1/14_Matmul_for_upper_triangular_matrices",
        "return triu(torch.matmul(A, B))",
        ("triu_kernel",),
        edits=FILE_EDITS_FG,
        notes="Only the triu epilogue is FlagGems; the GEMM is torch.matmul (library).",
    ),
    S2Entry(
        "liger-rms-norm",
        _LG,
        "src/liger_kernel/ops/rms_norm.py",
        "L1/36_RMSNorm_",
        "weight = torch.ones(self.num_features, dtype=x.dtype, device=x.device)\n"
        "y = LigerRMSNormFunction.apply(x.movedim(1, -1), weight, self.eps, 0.0, 'llama')\n"
        "return y.movedim(-1, 1)",
        ("_rms_norm_forward_kernel",),
        edits=("liger-inline-utils",),
        notes="KernelBench normalises dim 1; the wrapper moves it last and uses weight=1, "
        "offset=0. Liger computes x * rsqrt(mean(x^2) + eps). File incorporates Unsloth "
        "code under Apache-2.0 (upstream header).",
    ),
    S2Entry(
        "liger-layer-norm",
        _LG,
        "src/liger_kernel/ops/layer_norm.py",
        "L1/40_LayerNorm",
        "y = LigerLayerNormFunction.apply(x.reshape(x.shape[0], -1), "
        "self.ln.weight.reshape(-1), self.ln.bias.reshape(-1), self.ln.eps)\n"
        "return y.reshape(x.shape)",
        ("_layer_norm_forward_kernel",),
        edits=("liger-inline-utils",),
        notes="calculate_settings refuses rows over 65,536 elements; the native row is "
        "4,194,304 elements, so a native-shape refusal is expected.",
    ),
    S2Entry(
        "liger-cross-entropy",
        _LG,
        "src/liger_kernel/ops/cross_entropy.py",
        "L1/95_CrossEntropyLoss",
        "return LigerCrossEntropyFunction.apply(predictions.clone(), targets, -100, 0.0, 'mean')",
        ("liger_cross_entropy_kernel",),
        notes="Upstream forward writes gradients into its logits argument; the wrapper "
        "passes a clone so the KernelBench input is not modified.",
    ),
    S2Entry(
        "liger-kl-div",
        _LG,
        "src/liger_kernel/ops/kl_div.py",
        "L1/98_KLDivLoss",
        "return LigerKLDivLossFunction.apply(torch.log(predictions), targets, 'batchmean', False)",
        ("_kldiv_kernel_forward",),
        edits=("liger-inline-utils",),
        notes="torch.log(predictions) runs in the wrapper, as in the reference.",
    ),
    S2Entry(
        "tutorial-fused-softmax",
        _TT,
        "python/tutorials/02-fused-softmax.py",
        "L1/23_Softmax",
        "n_rows, n_cols = x.shape\n"
        "BLOCK_SIZE = triton.next_power_of_2(n_cols)\n"
        "y = torch.empty_like(x)\n"
        "softmax_kernel[(n_rows, 1, 1)](y, x, x.stride(0), y.stride(0), n_rows, n_cols, "
        "BLOCK_SIZE=BLOCK_SIZE, num_stages=4, num_warps=8)\n"
        "return y",
        ("softmax_kernel",),
        mode="names",
        names=("softmax_kernel",),
        notes="Host launch normalised: the tutorial warms up the kernel and launches the "
        "CompiledKernel with an occupancy-derived persistent grid (invisible to the "
        "launch hook); here it is a plain JIT launch with one program per row, num_warps=8 "
        "and num_stages=4 (the tutorial's value when shared memory exceeds 200 KB, as on "
        "H100). The kernel loops over rows, so the result does not depend on the grid.",
    ),
    *(
        S2Entry(
            "tutorial-matmul",
            _TT,
            "python/tutorials/03-matrix-multiplication.py",
            problem,
            "return matmul(A, B)",
            ("matmul_kernel",),
            mode="names",
            names=("get_cuda_autotune_config", "matmul_kernel", "leaky_relu", "matmul"),
            autotune_index={"matmul_kernel": 1},
            edits=(
                "tutorial-matmul-cuda-configs",
                "pin-autotune",
                "tutorial-matmul-store-dtype",
                "tutorial-matmul-output-dtype",
            ),
            notes="TF32-policy control: tl.dot at Triton's default input precision "
            "(tf32). fp16 output adapted to the fp32 output buffer. Config 0 "
            "(128x256x64, 3 stages) needs 294,912 B of shared memory at fp32 (> 232,448 B "
            "on sm_90), so config 1 is pinned.",
        )
        for problem in (
            "L1/1_Square_matrix_multiplication_",
            "L1/2_Standard_matrix_multiplication_",
            "L1/8_Matmul_with_irregular_shapes_",
        )
    ),
    S2Entry(
        "tutorial-layer-norm",
        _TT,
        "python/tutorials/05-layer-norm.py",
        "L1/40_LayerNorm",
        "y = LayerNorm.apply(x.reshape(x.shape[0], -1), (x[0].numel(),), "
        "self.ln.weight.reshape(-1), self.ln.bias.reshape(-1), self.ln.eps)\n"
        "return y.reshape(x.shape)",
        ("_layer_norm_fwd_fused",),
        mode="names",
        names=(
            "_layer_norm_fwd_fused",
            "_layer_norm_bwd_dx_fused",
            "_layer_norm_bwd_dwdb",
            "LayerNorm",
        ),
        notes="Upstream refuses feature sizes of 64 KB or more (16,384 fp32); the native "
        "row is 4,194,304 elements, so a native-shape refusal is expected.",
    ),
)


def entry(key_or_id: str) -> S2Entry:
    for item in CATALOG:
        if key_or_id in (item.substrate_id, item.key):
            return item
    raise KeyError(key_or_id)


# --- build --------------------------------------------------------------------------


def read_upstream(sources_root: Path, source: str, path: str) -> str:
    file = Path(sources_root) / SOURCE_DIRS[source] / path
    data = file.read_bytes()
    expected = UPSTREAM_FILES.get((source, path))
    if expected is None:
        raise S2BuildError(f"{source}:{path} is not pinned in UPSTREAM_FILES")
    size, digest = expected
    actual = hashlib.sha256(data).hexdigest()
    if len(data) != size or actual != digest:
        raise S2BuildError(f"{source}:{path} does not match its pin ({len(data)} B, {actual})")
    return data.decode("utf-8")


def _apply_edits(item: S2Entry, text: str, sources_root: Path) -> tuple[str, list[dict]]:
    steps: list[dict[str, str]] = []
    if item.mode == "names":
        text, detail = extract_names(text, item.names)
        steps.append({"name": "extract-definitions", "detail": detail})
    for edit in item.edits:
        if edit == "strip-libentry":
            text, detail = strip_libentry(text)
        elif edit == "drop-debug-prints":
            text, detail = drop_debug_prints(text)
        elif edit == "pin-autotune":
            text, detail = pin_autotune(text, item.autotune_index)
        elif edit == "tl-math-to-libdevice":
            text, detail = tl_math_to_libdevice(text)
        elif edit == "liger-inline-utils":
            utils = read_upstream(sources_root, "liger", "src/liger_kernel/ops/utils.py")
            text, detail = liger_inline_utils(text, utils)
        elif edit in TUTORIAL_EDITS:
            text, detail = TUTORIAL_EDITS[edit](text)
        else:
            raise S2BuildError(f"unknown edit {edit}")
        steps.append({"name": edit, "detail": detail})
    return text, steps


def _reference_for_s2(problem_source: str) -> tuple[str, ast.FunctionDef]:
    """Reference Model with imports and class/function defs only (no module constants)."""
    tree = ast.parse(problem_source)
    kept: list[ast.stmt] = []
    forward = None
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            kept.append(node)
        elif isinstance(node, ast.ClassDef) and node.name == "Model":
            kept.append(node)
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "forward":
                    forward = item
    if forward is None:
        raise S2BuildError("problem has no Model.forward")
    module = ast.Module(body=kept, type_ignores=[])
    _strip_docstrings(module)
    return ast.unparse(module).rstrip() + "\n", forward


def build_entry(item: S2Entry, sources_root: Path, kernelbench_root: Path) -> dict[str, Any]:
    """Build one S2 substrate; return {substrate_id, files, substrate_json, build_json}."""
    upstream = read_upstream(sources_root, item.source, item.path)
    normalised, steps = _apply_edits(item, upstream, sources_root)
    problem_source = problem_file(kernelbench_root, item.problem_id).read_text(encoding="utf-8")
    reference, forward = _reference_for_s2(problem_source)
    signature, arg_names = forward_signature(forward)
    body_names = {n.id for n in ast.walk(ast.parse(item.forward_body)) if isinstance(n, ast.Name)}
    if not set(arg_names) & body_names:
        raise S2BuildError(f"{item.key}: forward body uses none of {arg_names}")
    source = SOURCES[item.source]
    license_text = read_upstream(sources_root, item.source, "LICENSE")
    notice_text = read_upstream(sources_root, item.source, "NOTICE") if source.notice_file else None
    body = textwrap.indent(item.forward_body.strip() + "\n", " " * 8)
    header = textwrap.dedent(f'''\
        """Q1 S2 substrate {item.substrate_id}: human-written Triton.

        KernelBench problem: {item.problem_id}.

        Upstream: {source.repo} @ {source.revision} ({source.tag or "untagged"}), {item.path}
        Licence: {source.license}; upstream LICENSE{" and NOTICE" if notice_text else ""} are
        copied beside this file ({
        "LICENSE.upstream, NOTICE.upstream" if notice_text else "LICENSE.upstream"
    }).
        This file is a modified copy: the changes are listed in substrate.json and the full
        diff is normalization.diff. ModelNew below is harness glue (reviewed project code),
        not upstream code. Forward kernels: {", ".join(item.forward_kernels)}.
        """
        ''')
    model_new = (
        "\n\n# --- Reference Model from KernelBench (MIT), docstrings dropped; ModelNew inherits "
        "it ---\n" + reference + "\n\nclass ModelNew(Model):\n"
        f'    """{item.key} for {item.problem_id}; same constructor as Model."""\n\n'
        f"    def forward({signature}):\n{body}"
    )
    kernel_py = header + "\n# --- Upstream code (normalised) ---\n" + normalised + model_new
    compile(kernel_py, "kernel.py", "exec")
    diff = "".join(
        difflib.unified_diff(
            upstream.splitlines(keepends=True),
            normalised.splitlines(keepends=True),
            fromfile=f"upstream/{item.path}",
            tofile="normalised",
        )
    )
    transformations = [*steps]
    transformations.append(
        {
            "name": "normalization-diff",
            "detail": "unified diff upstream file -> normalised upstream code (normalization.diff)",
            "diff_sha256": sha256_text(diff),
        }
    )
    transformations.append(
        {
            "name": "modelnew-wrapper",
            "detail": "embedded reference Model (KernelBench, MIT; imports and "
            "class only); ModelNew.forward: " + item.forward_body.replace("\n", "; "),
        }
    )
    files = {
        "kernel.py": kernel_py,
        "normalization.diff": diff,
        "upstream_excerpt.py.txt": upstream,
        "LICENSE.upstream": license_text,
    }
    if notice_text:
        files["NOTICE.upstream"] = notice_text
    level, _, _ = parse_problem_id(item.problem_id)
    build = {
        "s2_build_version": S2_BUILD_VERSION,
        "key": item.key,
        "problem_id": item.problem_id,
        "problem_sha256": sha256_text(problem_source),
        "source": item.source,
        "upstream_path": item.path,
        "upstream_sha256": UPSTREAM_FILES[(item.source, item.path)][1],
        "forward_kernels": list(item.forward_kernels),
        "source_kernel_family": item.kernel_family,
        "autotune_index": item.autotune_index,
        "edits": list(item.edits),
        "triton_coverage": "hybrid-library"
        if "torch.matmul" in item.forward_body
        else "triton-only",
    }
    files["build.json"] = json.dumps(build, indent=1, sort_keys=True) + "\n"
    substrate = {
        "substrate_id": item.substrate_id,
        "problem_id": item.problem_id,
        "level": level,
        "kernelbench_revision": KERNELBENCH_PROBLEMS_REVISION,
        "source_kind": source.source_kind,
        "source_repo": source.repo,
        "source_revision": source.revision,
        "source_license": source.license,
        "origin_path": item.path,
        "transformations": transformations,
        "notes": item.notes or "Human-written pre-2025 Triton; see transformations.",
        "schema_version": SCHEMA_VERSION,
        "files": [
            {"path": name, "sha256": sha256_text(text)} for name, text in sorted(files.items())
        ],
    }
    validate_substrate(substrate)
    return {
        "substrate_id": item.substrate_id,
        "files": files,
        "substrate_json": substrate,
        "build_json": build,
    }


def build_all(
    sources_root: Path,
    kernelbench_root: Path,
    out_root: Path,
    *,
    force: bool = False,
    only: list[str] | None = None,
) -> list[dict[str, Any]]:
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in CATALOG:
        if only and item.key not in only and item.substrate_id not in only:
            continue
        try:
            built = build_entry(item, sources_root, kernelbench_root)
        except (S2BuildError, OSError, SyntaxError) as exc:
            rows.append(
                {
                    "substrate_id": item.substrate_id,
                    "status": "build-error",
                    "reason": str(exc)[:500],
                }
            )
            continue
        directory = out_root / item.substrate_id
        if directory.exists() and not force:
            rows.append({"substrate_id": item.substrate_id, "status": "exists"})
            continue
        directory.mkdir(parents=True, exist_ok=True)
        for name, text in built["files"].items():
            (directory / name).write_text(text, encoding="utf-8")
        (directory / "substrate.json").write_text(
            json.dumps(built["substrate_json"], indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        rows.append(
            {
                "substrate_id": item.substrate_id,
                "status": "built",
                "problem_id": item.problem_id,
                "source": item.source,
            }
        )
    return rows


def verify_vendored_sources(root: Path = VENDORED_SOURCES_ROOT) -> list[str]:
    """Check every pinned upstream file in ``root``; return the paths that verified."""
    verified = []
    for source, path in sorted(UPSTREAM_FILES):
        read_upstream(root, source, path)
        verified.append(f"{SOURCE_DIRS[source]}/{path}")
    return verified
