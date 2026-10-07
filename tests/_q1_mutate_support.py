"""Shared helpers for the Q1 mutator tests (not collected by pytest)."""

from __future__ import annotations

import json
from pathlib import Path

from harness.q1.schema import KERNELBENCH_PROBLEMS_REVISION, SCHEMA_VERSION

TOY_DIR = Path(__file__).resolve().parent / "data" / "q1_toy_kernels"
TOYS = sorted(p.stem for p in TOY_DIR.glob("*.py"))

# Toy kernel -> the KernelBench problem it stands in for in corpus tests.
TOY_PROBLEMS = {
    "relu_where": "L1/19_ReLU",
    "relu_inductor": "L1/19_ReLU",
    "softmax_rows": "L1/23_Softmax",
    "layernorm": "L1/40_LayerNorm",
    "matmul": "L1/1_Square_matrix_multiplication_",
    "argmax_rows": "L1/51_Argmax_over_a_dimension",
    "gelu_erf": "L1/26_GELU_",
    "splitk_atomic": "L1/47_Sum_reduction_over_a_dimension",
    "activations": "L1/32_HardTanh",
    "reductions_misc": "L1/49_Max_reduction_over_a_dimension",
}

# A minimal stand-in for a KernelBench problem file (same structure as
# KernelBench's level1 files; written for the tests).
RELU_PROBLEM = """import torch
import torch.nn as nn


class Model(nn.Module):
    def __init__(self):
        super(Model, self).__init__()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.relu(x)


batch_size = 4096
dim = 393216


def get_inputs():
    x = torch.rand(batch_size, dim)
    return [x]


def get_init_inputs():
    return []
"""

SOFTMAX_PROBLEM = RELU_PROBLEM.replace("torch.relu(x)", "torch.softmax(x, dim=1)")


def toy_text(name: str) -> str:
    return (TOY_DIR / f"{name}.py").read_text()


def substrate_record(substrate_id: str, problem_id: str) -> dict:
    level = int(problem_id[1])
    return {
        "substrate_id": substrate_id,
        "problem_id": problem_id,
        "level": level,
        "kernelbench_revision": KERNELBENCH_PROBLEMS_REVISION,
        "source_kind": "triton-tutorial",
        "source_repo": "https://github.com/triton-lang/triton",
        "source_revision": "a" * 40,
        "source_license": "MIT",
        "origin_path": "python/tutorials/toy.py",
        "transformations": [{"name": "toy", "detail": "test substrate"}],
        "schema_version": SCHEMA_VERSION,
    }


def make_substrates(root: Path, toys: list[str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name in toys:
        substrate_id = f"toy-{name.replace('_', '-')}"
        target = root / substrate_id
        target.mkdir()
        (target / "kernel.py").write_text(toy_text(name))
        (target / "substrate.json").write_text(
            json.dumps(substrate_record(substrate_id, TOY_PROBLEMS[name]), indent=1)
        )
    return root


def make_kernelbench(root: Path) -> Path:
    level1 = root / "KernelBench" / "level1"
    level1.mkdir(parents=True)
    (level1 / "19_ReLU.py").write_text(RELU_PROBLEM)
    (level1 / "23_Softmax.py").write_text(SOFTMAX_PROBLEM)
    return root
