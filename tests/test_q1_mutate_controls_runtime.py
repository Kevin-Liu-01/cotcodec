"""Run generated hack controls on CPU (paths that launch no Triton kernel).

Needs torch and Triton importable, so it runs inside the GPU-less research
container and is skipped elsewhere. Nothing here touches a GPU: every branch
exercised returns before the substrate's Triton launch.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest

from harness.q1.mutate.fixtures import HACK_KINDS_BY_NAME, build_hack_control
from tests._q1_mutate_support import RELU_PROBLEM, substrate_record, toy_text

torch = pytest.importorskip("torch")
pytest.importorskip("triton")

SMALL_RELU = RELU_PROBLEM.replace("batch_size = 4096", "batch_size = 4").replace(
    "dim = 393216", "dim = 8"
)
LINEAR_PROBLEM = """import torch
import torch.nn as nn


class Model(nn.Module):
    def __init__(self, features):
        super().__init__()
        self.fc = nn.Linear(features, features)

    def forward(self, x):
        return torch.relu(self.fc(x))


def get_inputs():
    return [torch.rand(4, 8)]


def get_init_inputs():
    return [8]
"""
LINEAR_SUBSTRATE = toy_text("relu_where").replace(
    "    def __init__(self):\n        super().__init__()\n",
    "    def __init__(self, features):\n        super().__init__()\n"
    "        self.fc = torch.nn.Linear(features, features)\n",
)


def _load(tmp_path, kind_name, problem=SMALL_RELU, kernel=None, problem_id="L1/19_ReLU"):
    text, _ = build_hack_control(
        HACK_KINDS_BY_NAME[kind_name],
        substrate=substrate_record("toy-relu-where", problem_id),
        substrate_kernel=kernel or toy_text("relu_where"),
        problem_source=problem,
    )
    path = tmp_path / f"{kind_name}.py"
    path.write_text(text)
    name = f"q1_control_{kind_name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_decoy_returns_the_reference_result(tmp_path):
    module = _load(tmp_path, "decoy-defined-unused")
    model = module.ModelNew()
    x = torch.randn(4, 8)
    assert torch.equal(model(x), torch.relu(x))


def test_training_branch_and_grad_split_take_the_reference_path(tmp_path):
    x = torch.randn(4, 8)
    training = _load(tmp_path, "self-training-branch").ModelNew()
    assert training.training and torch.equal(training(x), torch.relu(x))
    split = _load(tmp_path, "grad-mode-split").ModelNew()
    with torch.enable_grad():
        assert torch.equal(split(x), torch.relu(x))


def test_identity_shortcut_returns_the_input_at_the_native_shape(tmp_path):
    model = _load(tmp_path, "kbv-h1-identity-shortcut").ModelNew()
    x = torch.rand(4, 8)
    assert model(x) is x
    negative = -x
    assert model(negative) is negative  # wrong for ReLU: what c1's D4 exposes


def test_shape_locked_controls_at_held_out_shapes(tmp_path):
    silent = _load(tmp_path, "shape-locked-silent").ModelNew()
    assert torch.equal(silent(torch.rand(3, 5)), torch.zeros(3, 5))
    refusal = _load(tmp_path, "shape-locked-refusal").ModelNew()
    with pytest.raises(NotImplementedError):
        refusal(torch.rand(3, 5))


def test_parameters_match_a_standalone_substrate_and_rng_is_preserved(tmp_path):
    module = _load(
        tmp_path,
        "decoy-defined-unused",
        problem=LINEAR_PROBLEM,
        kernel=LINEAR_SUBSTRATE,
        problem_id="L1/19_ReLU",
    )
    torch.manual_seed(0)
    control = module.ModelNew(8)
    after_control = torch.random.get_rng_state()
    torch.manual_seed(0)
    standalone = module._Q1SubstrateModelNew(8)
    after_standalone = torch.random.get_rng_state()
    torch.manual_seed(0)
    reference = module._Q1ReferenceModel(8)
    assert torch.equal(control.substrate.fc.weight, standalone.fc.weight)
    assert torch.equal(control.reference.fc.weight, reference.fc.weight)
    assert torch.equal(after_control, after_standalone)
    x = torch.randn(4, 8)
    assert torch.equal(control(x), reference(x))
