"""Tests for the Q1 substrate builders (no torch, no triton, no GPU).

Fixtures under tests/fixtures/q1_substrates/ are real codegen records written
by harness/q1/substrates/inductor_codegen.py in mock-H100 mode (torch 2.11.0,
Triton 3.6.0) for five KernelBench@423217d9 problems.
"""

from __future__ import annotations

import ast
import copy
import json
import re
from pathlib import Path

import pytest

from harness.q1 import schema
from harness.q1.substrates import admission, inductor_convert, s2_catalog, sources, split
from harness.q1.substrates.inductor_convert import ConversionError, convert_record

FIXTURES = Path(__file__).parent / "fixtures" / "q1_substrates"
RECORDS = sorted(FIXTURES.glob("L*__*.json"))


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def write_substrate(tmp_path: Path, converted) -> Path:
    directory = tmp_path / converted.substrate_id
    directory.mkdir()
    for name, text in converted.files().items():
        (directory / name).write_text(text, encoding="utf-8")
    (directory / "substrate.json").write_text(
        json.dumps(converted.substrate_json), encoding="utf-8"
    )
    return directory


# --- conversion -------------------------------------------------------------------


@pytest.mark.parametrize("record_path", RECORDS, ids=[p.stem for p in RECORDS])
def test_fixture_records_convert_and_validate(record_path: Path, tmp_path: Path) -> None:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    converted = convert_record(record)
    schema.validate_substrate(converted.substrate_json)
    tree = ast.parse(converted.kernel_py)
    jit = admission.jit_functions(tree)
    assert jit, "no @triton.jit kernel survived"
    text = converted.kernel_py
    assert "triton_heuristics" not in text
    assert ".run(" not in text
    assert "stream=" not in text
    assert "get_raw_stream" not in text
    # Every Inductor kernel is launched through kernel[grid](...).
    sites = admission.launch_sites(tree, set(jit))
    launched = {site["kernel"] for site in sites if site["kind"] == "subscript"}
    assert {k["name"] for k in record["kernels"]} <= launched
    # Inductor's compile options travel with each launch.
    assert "debug=True" in text and "sanitize_overflow=False" in text
    # KernelBench's strict static patterns must not be triggered by the packaging.
    stripped = re.sub(r"(?m)#.*$", "", text)
    for pattern in admission.STRICT_STATIC_PATTERNS.values():
        assert not re.search(pattern, stripped), pattern
    directory = write_substrate(tmp_path, converted)
    row = admission.static_check(directory)
    assert row["verdict"] == "pass", row["reasons"]
    assert schema.load_kernel_dir(directory).kind == "substrate"


def test_relu_conversion_keeps_kernel_text_and_binds_inputs() -> None:
    record = load("L1__19_ReLU")
    converted = convert_record(record)
    kernel_source = record["kernels"][0]["source"]
    body = kernel_source[kernel_source.index("@triton.jit") :].strip()
    assert body in converted.kernel_py, "kernel text must be copied verbatim"
    assert "L['x'].size()[0]" in converted.kernel_py
    assert "class ModelNew(Model):" in converted.kernel_py
    assert "_DeviceGuard(device_index)" in converted.kernel_py
    assert "s27*s77 <= 2147483647" in converted.kernel_py
    # Dynamo's 0/1 specialisation becomes a refusal below size 2.
    assert ">= 2" in converted.kernel_py
    assert converted.build_json["triton_coverage"] == "triton-only"
    assert converted.substrate_json["source_kind"] == "inductor"
    assert converted.substrate_json["source_revision"] == sources.SOURCES["pytorch"].revision


def test_template_kernel_uses_fixed_grid_from_launcher_args() -> None:
    converted = convert_record(load("L1__1_Square_matrix_multiplication_"))
    assert "triton_tem_fused_mm_0[(" in converted.kernel_py
    assert "_grid_triton_tem" not in converted.kernel_py
    assert converted.build_json["gemm_choice_rule"]


def test_scan_helper_is_kept_as_jit_function() -> None:
    converted = convert_record(load("L1__89_cumsum"))
    tree = ast.parse(converted.kernel_py)
    assert "_triton_helper_fn_add0" in admission.jit_functions(tree)


def test_conv_problem_is_hybrid_library() -> None:
    converted = convert_record(load("L2__1_Conv2D_ReLU_BiasAdd"))
    assert converted.build_json["triton_coverage"] == "hybrid-library"
    assert any("convolution" in call for call in converted.build_json["library_calls"])


def test_normalization_diff_hash_matches_file() -> None:
    converted = convert_record(load("L1__23_Softmax"))
    step = next(
        t for t in converted.substrate_json["transformations"] if t["name"] == "normalization-diff"
    )
    assert step["diff_sha256"] == inductor_convert.sha256_text(
        converted.extra_files["normalization.diff"]
    )
    listed = {entry["path"]: entry["sha256"] for entry in converted.substrate_json["files"]}
    for name, text in converted.files().items():
        assert listed[name] == inductor_convert.sha256_text(text)


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda r: r["fw_metadata"].update(output_types=["alias_of_input"]), "aliased-output"),
        (
            lambda r: r["fw_metadata"].update(mutated_inp_runtime_indices=[0]),
            "runtime-input-mutation",
        ),
        (lambda r: r["fw_metadata"].update(is_rng_op_functionalized=True), "aot-runtime-epilogue"),
        (lambda r: r.update(kernels=[]), "no-triton-kernel"),
        (lambda r: r.update(graph_outputs=2), "output-count-mismatch"),
        (lambda r: r["kernels"][0]["configs"].clear(), "no-config"),
        (
            lambda r: r["kernels"][0]["grid"].update(x="triton.cdiv(mystery, XBLOCK)"),
            "unsupported-grid",
        ),
        (lambda r: r["placeholders"].pop(0), "call-arity"),
        (
            lambda r: r.update(
                output_code=r["output_code"].replace(
                    "triton_poi_fused_relu_0.run(", "other_kernel.run("
                )
            ),
            "unconverted-launch",
        ),
        (lambda r: r["versions"].update(torch_git="0" * 40), "torch-revision-mismatch"),
    ],
)
def test_unfaithful_records_are_refused(mutate, reason) -> None:
    record = copy.deepcopy(load("L1__19_ReLU"))
    mutate(record)
    with pytest.raises(ConversionError) as excinfo:
        convert_record(record)
    assert excinfo.value.reason == reason


def test_training_dependent_modules_get_a_training_guard() -> None:
    record = copy.deepcopy(load("L1__19_ReLU"))
    record["module_types"] = ["BatchNorm2d", "Model"]
    converted = convert_record(record)
    assert "if not self.training:" in converted.kernel_py
    assert converted.build_json["training_guard"] == ["BatchNorm2d"]


def test_reference_model_drops_docstrings_and_get_inputs() -> None:
    record = load("L1__23_Softmax")
    text, forward = inductor_convert.reference_model_source(record["problem_source"])
    assert "def get_inputs" not in text and "def get_init_inputs" not in text
    assert '"""' not in text
    assert forward.name == "forward"
    signature, names = inductor_convert.forward_signature(forward)
    assert names == ["x"]


# --- static admission -------------------------------------------------------------


def _tamper(directory: Path, old: str, new: str) -> None:
    path = directory / "kernel.py"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_static_check_rejects_libentry_and_direct_run(tmp_path: Path) -> None:
    converted = convert_record(load("L1__19_ReLU"))
    directory = write_substrate(tmp_path, converted)
    _tamper(directory, "@triton.jit\n", "@libentry()\n@triton.jit\n")
    row = admission.static_check(directory)
    assert row["verdict"] == "fail"
    assert any("libentry" in reason for reason in row["reasons"])

    other = tmp_path / "other"
    other.mkdir()
    directory2 = write_substrate(other, converted)
    _tamper(
        directory2,
        "triton_poi_fused_relu_0[_grid_triton_poi_fused_relu_0](",
        "triton_poi_fused_relu_0.run(",
    )
    row2 = admission.static_check(directory2)
    assert row2["verdict"] == "fail"
    assert any("direct" in reason or "no kernel[grid]" in reason for reason in row2["reasons"])


def test_static_check_requires_modelnew(tmp_path: Path) -> None:
    directory = write_substrate(tmp_path, convert_record(load("L1__19_ReLU")))
    _tamper(directory, "class ModelNew(Model):", "class ModelOther(Model):")
    row = admission.static_check(directory)
    assert row["verdict"] == "fail"


# --- small-input shrinking (pure AST parts) ------------------------------------------


PROBLEM = """
import torch
import torch.nn as nn

class Model(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, 3)
    def forward(self, x):
        return self.conv(x)

batch_size = 128
in_channels = 64
out_channels = 2 * 64
height = width = 128
depth, extra = 32, 7

def get_inputs():
    return [torch.rand(batch_size, in_channels, height, width)]

def get_init_inputs():
    return [in_channels, out_channels]
"""


def test_shrinkable_sizes_freeze_init_dependencies() -> None:
    sizes, frozen = admission.shrinkable_sizes(PROBLEM)
    assert sizes == {
        "batch_size": 128,
        "in_channels": 64,
        "out_channels": 128,
        "height": 128,
        "width": 128,
        "depth": 32,
        "extra": 7,
    }
    assert {"in_channels", "out_channels"} <= frozen
    assert "batch_size" not in frozen and "height" not in frozen


def test_shrunk_source_rewrites_chained_and_tuple_assignments() -> None:
    text = admission.shrunk_source(PROBLEM, {"height": 4, "width": 4, "depth": 2, "batch_size": 2})
    namespace: dict = {}
    exec(
        compile(text.replace("import torch\nimport torch.nn as nn\n", ""), "p", "exec"),  # noqa: S102
        {"nn": type("nn", (), {"Module": object})},
        namespace,
    )
    assert namespace["height"] == 4 and namespace["width"] == 4
    assert namespace["depth"] == 2 and namespace["extra"] == 7
    assert namespace["in_channels"] == 64


def test_candidate_overrides_never_go_below_two() -> None:
    candidates = admission.candidate_overrides(PROBLEM)
    assert candidates[0]["batch_size"] == 128
    assert all(value >= 2 for override in candidates for value in override.values())
    assert candidates[-1]["batch_size"] == 2


# --- split ------------------------------------------------------------------------


def _all_problem_ids() -> list[str]:
    ids = [f"L1/{n}_P{n}" for n in range(1, 101)]
    ids += [f"L2/{n}_Q{n}" for n in range(1, 101)]
    return ids


def test_split_is_deterministic_stratified_and_excludes() -> None:
    ids = _all_problem_ids() + list(sources.EXCLUDED_PROBLEMS)
    first = split.calibration_split(ids, seed=42)
    second = split.calibration_split(list(reversed(ids)), seed=42)
    assert first == second
    cal, ev = set(first["calibration"]), set(first["evaluation"])
    assert not cal & ev
    assert not (cal | ev) & set(sources.EXCLUDED_PROBLEMS)
    for level in (1, 2):
        in_cal = sum(1 for pid in cal if pid.startswith(f"L{level}/"))
        in_eval = sum(1 for pid in ev if pid.startswith(f"L{level}/"))
        assert in_cal - in_eval in (0, 1)
    assert split.calibration_split(ids, seed=43)["calibration"] != first["calibration"]
    assert split.half_of(first["evaluation"][0], first) == "evaluation"


# --- S2 transformations and catalog ----------------------------------------------


FLAGGEMS_SNIPPET = """import torch
import triton
import triton.language as tl
from .__libentry__ import libentry


@libentry()
@triton.autotune(
    configs=[
        triton.Config({"B": 256}, num_warps=2),
        triton.Config({"B": 512}, num_warps=4),
    ],
    key=["M"],
)
@triton.jit
def k(X, Y, M, B: tl.constexpr):
    x = tl.math.tanh(tl.load(X))
    tl.store(Y, tl.math.pow(x, 2.0))


def host(A):
    if __debug__:
        print("GEMS HOST")
    return A
"""


def test_s2_text_transformations() -> None:
    text, _ = s2_catalog.strip_libentry(FLAGGEMS_SNIPPET)
    assert "libentry" not in text
    text, _ = s2_catalog.drop_debug_prints(text)
    assert "__debug__" not in text and "print" not in text
    text, detail = s2_catalog.pin_autotune(text, {"k": 1})
    assert "configs=([" in text and ")[1:2]" in text and "k[1]" in detail
    text, _ = s2_catalog.tl_math_to_libdevice(text)
    assert "tl.math.tanh" not in text and "libdevice.tanh(" in text and "libdevice.pow(" in text
    assert "from triton.language.extra import libdevice" in text
    compile(text, "snippet", "exec")
    with pytest.raises(s2_catalog.S2BuildError):
        s2_catalog.strip_libentry(text)
    with pytest.raises(s2_catalog.S2BuildError):
        s2_catalog.pin_autotune(text, {"missing": 0})


def test_liger_inline_utils_replaces_imports() -> None:
    ops = (
        "import operator\nimport torch\nimport triton\n\n"
        "from liger_kernel.ops.utils import (\n    calculate_settings,\n    compare_version,\n"
        "    ensure_contiguous,\n)\n\n"
        'if compare_version("triton", operator.ge, "3.0.0"):\n'
        "    from triton.language.extra.libdevice import rsqrt\n"
        "else:\n    from triton.language.math import rsqrt\n"
    )
    utils = (
        "import functools\n\n\ndef ensure_contiguous(fn):\n    return fn\n\n\n"
        "def calculate_settings(n):\n    return n, 4\n\n\n"
        "def compare_version(package, operator, target):\n    return True\n"
    )
    text, detail = s2_catalog.liger_inline_utils(ops, utils)
    assert "liger_kernel" not in text and "compare_version(" not in text
    assert "def calculate_settings" in text and "def ensure_contiguous" in text
    assert "from triton.language.extra.libdevice import rsqrt" in text
    compile(text, "ops", "exec")
    assert "inlined" in detail


def test_extract_names_keeps_imports_and_definitions() -> None:
    script = (
        "import torch\nimport triton\nfrom triton.runtime import driver\n\n"
        "DEVICE = triton.runtime.driver.active.get_active_torch_device()\n\n"
        "@triton.jit\ndef kern(x):\n    return x\n\n\ndef other():\n    return 1\n\n"
        "print(kern)\n"
    )
    text, _ = s2_catalog.extract_names(script, ("kern",))
    assert "DEVICE" not in text and "def other" not in text and "print(kern)" not in text
    assert "@triton.jit\ndef kern" in text and "driver" not in text


def test_s2_catalog_integrity() -> None:
    ids = [item.substrate_id for item in s2_catalog.CATALOG]
    assert len(ids) == len(set(ids))
    for item in s2_catalog.CATALOG:
        assert (item.source, item.path) in s2_catalog.UPSTREAM_FILES
        assert (item.source, "LICENSE") in s2_catalog.UPSTREAM_FILES
        assert sources.is_admissible_problem(item.problem_id)
        assert item.forward_kernels
        assert schema.KERNEL_ID_RE.fullmatch(item.substrate_id)
        source = sources.SOURCES[item.source]
        assert source.source_kind in schema.SOURCE_KINDS
        assert source.license in schema.SOURCE_LICENSES
        for edit in item.edits:
            assert edit in {
                "strip-libentry",
                "drop-debug-prints",
                "pin-autotune",
                "tl-math-to-libdevice",
                "liger-inline-utils",
                *s2_catalog.TUTORIAL_EDITS,
            }
    kinds = {sources.SOURCES[item.source].source_kind for item in s2_catalog.CATALOG}
    assert kinds == {"flaggems", "liger", "triton-tutorial"}


def test_sources_are_pinned_and_licensed() -> None:
    for source in sources.SOURCES.values():
        assert schema.HEX40_RE.fullmatch(source.revision), source.key
        assert source.license in schema.SOURCE_LICENSES
    assert sources.SOURCES["flaggems"].license == "Apache-2.0"
    assert sources.SOURCES["liger"].license == "BSD-2-Clause"
    assert sources.SOURCES["triton-tutorials"].license == "MIT"
    assert sources.SOURCES["kernelbench"].revision == schema.KERNELBENCH_PROBLEMS_REVISION
    assert not sources.is_admissible_problem("L2/66_Matmul_Dropout_Softmax")
    assert sources.is_admissible_problem("L1/19_ReLU")
    assert not sources.is_admissible_problem("L3/1_MLP")


def test_corpus_manifest_reports_split_half(tmp_path: Path) -> None:
    converted = convert_record(load("L1__19_ReLU"))
    write_substrate(tmp_path, converted)
    (tmp_path / "check_static.json").write_text(
        json.dumps({"rows": [admission.static_check(tmp_path / converted.substrate_id)]}),
        encoding="utf-8",
    )
    split_path = tmp_path / "split.json"
    split_path.write_text(
        json.dumps(split.calibration_split(["L1/19_ReLU", "L1/20_LeakyReLU"])), encoding="utf-8"
    )
    manifest = admission.corpus_manifest(tmp_path, split_path)
    row = manifest["rows"][0]
    assert row["check_static"] == "pass"
    assert row["split_half"] in ("calibration", "evaluation")
    assert manifest["summary"]["substrates"] == 1
