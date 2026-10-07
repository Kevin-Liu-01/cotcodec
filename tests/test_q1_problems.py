"""Problem pinning, constant analysis, shape rules and committed Q1 data files.

Pure Python: runs without torch.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.q1 import problems, shapes
from harness.q1.gates.outcome import channel_seed
from harness.q1.schema import CONFIG_ID_RE, KBV_REVISION, KERNELBENCH_PROBLEMS_REVISION

Q1 = Path(problems.__file__).resolve().parent
DATA = Q1 / "data"


def test_problem_hash_table_covers_every_vendored_file() -> None:
    table = problems.problem_hashes()
    assert len(table) == 200
    on_disk = {
        f"L{level}/{path.stem}"
        for level in (1, 2)
        for path in (problems.PROBLEMS_ROOT / f"level{level}").glob("*.py")
    }
    assert on_disk == set(table)
    for problem_id in ("L1/19_ReLU", "L1/95_CrossEntropyLoss", "L2/12_Gemm_Multiply_LeakyReLU"):
        data = problems.problem_path(problem_id).read_bytes()
        assert hashlib.sha256(data).hexdigest() == table[problem_id]


def test_excluded_problems_exist_and_are_dropped() -> None:
    every = problems.list_problem_ids(include_excluded=True)
    kept = problems.list_problem_ids()
    assert set(problems.EXCLUDED_PROBLEMS) <= set(every)
    assert not set(problems.EXCLUDED_PROBLEMS) & set(kept)
    assert len(kept) == 196


def test_load_refuses_a_tampered_problem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_root = tmp_path / "problems"
    (fake_root / "level1").mkdir(parents=True)
    original = problems.problem_path("L1/19_ReLU").read_text()
    (fake_root / "level1" / "19_ReLU.py").write_text(original.replace("4096", "4095"))
    monkeypatch.setattr(problems, "PROBLEMS_ROOT", fake_root)
    with pytest.raises(problems.ProblemError, match="hash"):
        problems.load_problem_source("L1/19_ReLU")
    assert "4095" in problems.load_problem_source("L1/19_ReLU", verify=False)


def test_constant_classification() -> None:
    relu = problems.analyze_problem("L1/19_ReLU")
    assert relu.free_roots == ("batch_size", "dim")
    assert (relu.leading, relu.inner) == ("batch_size", "dim")
    gemm = problems.analyze_problem("L2/12_Gemm_Multiply_LeakyReLU")
    assert gemm.free_roots == ("batch_size",)
    assert {"in_features", "out_features"} <= gemm.init_bound
    ce = problems.analyze_problem("L1/95_CrossEntropyLoss")
    assert ce.free_roots == ("batch_size", "num_classes")
    hinge = problems.analyze_problem("L1/100_HingeLoss")
    assert hinge.free_roots == ("batch_size", "input_shape[0]")
    matmul = problems.analyze_problem("L1/2_Standard_matrix_multiplication_")
    assert matmul.is_matmul and matmul.free_roots == ("M", "K", "N")
    assert not problems.analyze_problem("L1/5_Matrix_scalar_multiplication").is_matmul


def test_model_bound_constants_stay_fixed() -> None:
    source = (
        "import torch\nimport torch.nn as nn\n\nclass Model(nn.Module):\n"
        "    def __init__(self):\n        super().__init__()\n\n"
        "    def forward(self, x):\n        return x.view(batch_size, -1)\n\n"
        "batch_size = 8\ndim = 16\n\n"
        "def get_inputs():\n    return [torch.rand(batch_size, dim)]\n\n"
        "def get_init_inputs():\n    return []\n"
    )
    analysis = problems.analyze_problem("L1/9100_ModelReadsGlobal", source)
    assert analysis.free_roots == ("dim",)
    assert "batch_size" in analysis.model_bound


def test_override_rewrites_only_value_spans() -> None:
    source = problems.load_problem_source("L1/100_HingeLoss")
    analysis = problems.analyze_problem("L1/100_HingeLoss", source)
    changed = problems.override_constants(source, analysis, {"input_shape[0]": 17, "batch_size": 3})
    assert "input_shape = (17,)" in changed and "batch_size = 3" in changed
    before = source.replace("batch_size = 32768", "").replace("input_shape = (32768,)", "")
    after = changed.replace("batch_size = 3", "").replace("input_shape = (17,)", "")
    assert before == after
    with pytest.raises(problems.ProblemError):
        problems.override_constants(source, analysis, {"dim": 2})
    with pytest.raises(problems.ProblemError):
        problems.override_constants(source, analysis, {"batch_size": 0})


def _fake_bytes(analysis: problems.ProblemAnalysis):
    native = analysis.native_values()

    def input_bytes(overrides: dict[str, int]) -> int:
        values = {**native, **overrides}
        total = 1
        for value in values.values():
            total *= value
        return 4 * total

    return input_bytes


def test_shape_rules_on_a_matmul_problem() -> None:
    analysis = problems.analyze_problem("L1/2_Standard_matrix_multiplication_")
    entry = shapes.build_problem_manifest(
        analysis, problem_sha256="0" * 64, input_bytes=_fake_bytes(analysis)
    )
    ids = {c["config_id"]: c["overrides"] for c in entry["c2"] + entry["c3"] + entry["A3"]}
    assert ids["c2/S-half"] == {"M": 1024}
    assert ids["c2/S-double"] == {"N": 8192}
    assert ids["c3/U2/K"] == {"K": 8209}
    assert ids["c3/MM17"] == {"K": 8209, "M": 2065, "N": 4113}
    assert ids["c3/U3"] == {"M": 3}
    assert ids["A3/lead5"] == {"M": 5}
    assert shapes.is_prime(ids["A3/inner37"]["N"])
    c_values: dict[str, set[int]] = {}
    for config in entry["c2"] + entry["c3"]:
        for root, value in config["overrides"].items():
            c_values.setdefault(root, set()).add(value)
    for config in entry["A3"]:
        for root, value in config["overrides"].items():
            assert value not in c_values.get(root, set())


def test_byte_cap_shrinks_s_double() -> None:
    analysis = problems.analyze_problem("L1/1_Square_matrix_multiplication_")

    def two_square_inputs(overrides: dict[str, int]) -> int:  # A and B are N x N fp32
        n_value = overrides.get("N", analysis.native_values()["N"])
        return 2 * 4 * n_value * n_value

    entry = shapes.build_problem_manifest(
        analysis, problem_sha256="0" * 64, input_bytes=two_square_inputs
    )
    double = next(c for c in entry["c2"] if c["config_id"] == "c2/S-double")
    n = analysis.native_values()["N"]
    capped = double["overrides"]["N"]
    assert double["capped_from"] == 2 * n
    assert n < capped < 2 * n
    assert capped**2 <= 2 * n**2 < (capped + 1) ** 2


def test_committed_shape_manifest_is_consistent() -> None:
    manifest = json.loads((DATA / "shape_manifest.json").read_text())
    assert manifest["schema"] == shapes.MANIFEST_SCHEMA
    assert manifest["kernelbench_revision"] == KERNELBENCH_PROBLEMS_REVISION
    assert set(manifest["problems"]) == set(problems.list_problem_ids())
    table = problems.problem_hashes()
    for problem_id, entry in manifest["problems"].items():
        assert entry["problem_sha256"] == table[problem_id]
        roots = set(entry["free_roots"])
        native = entry["native"]["values"]
        for family in ("c2", "c3", "A3"):
            for config in entry[family]:
                assert set(config["overrides"]) <= roots
                assert config["init_inputs_unchanged"] is True
                assert config["input_bytes"] <= 2 * entry["native"]["input_bytes"]
                assert {**native, **config["overrides"]} != native


def test_committed_kbv_config_table() -> None:
    table = json.loads((DATA / "kbv_hidden_configs.json").read_text())
    assert table["kbv_revision"] == KBV_REVISION
    entries = table["problems"]
    assert len(entries) == 200
    assert entries["L1/19_ReLU"]["configs"] == ["D1", "D2", "D3", "D4"]
    assert entries["L1/90_cumprod"]["configs"] == ["D1", "D3", "D4"]
    assert entries["L1/98_KLDivLoss"]["configs"] == ["D1", "D2", "D3"]
    assert entries["L1/100_HingeLoss"]["configs"][-1] == "D5-alternating-targets"


def test_every_committed_config_id_is_schema_valid_with_its_suffix() -> None:
    """Review finding: ``c3/U1/input_shape[0]`` broke CONFIG_ID_RE inside the worker,
    after the candidate ran, so gate (c) rejected every kernel on 10 L1 problems."""
    manifest = json.loads((DATA / "shape_manifest.json").read_text())
    longest_seed = channel_seed(5042, 44, 99)
    checked = 0
    for entry in manifest["problems"].values():
        for family in ("c2", "c3"):
            for config in entry[family]:
                for draw in ("D1", "D4"):
                    config_id = f"{config['config_id']}/{draw}/seed-{longest_seed}"
                    assert CONFIG_ID_RE.fullmatch(config_id), config_id
                    checked += 1
        for config in entry["A3"]:
            assert CONFIG_ID_RE.fullmatch(f"{config['config_id']}/seed-{longest_seed}")
            checked += 1
    assert checked == 2 * (587 + 915) + 865
    # Tuple-element roots keep their real name in the overrides, a safe label in the id.
    cumsum = {c["config_id"]: c["overrides"] for c in manifest["problems"]["L1/89_cumsum"]["c3"]}
    assert cumsum["c3/U1/input_shape.0"] == {"input_shape[0]": 32769}


def test_root_labels() -> None:
    assert shapes.root_label("input_shape[0]") == "input_shape.0"
    assert shapes.root_label("batch_size") == "batch_size"
    with pytest.raises(ValueError):
        shapes.root_label("bad root")
