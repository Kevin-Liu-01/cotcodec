"""Static reading of KernelBench get_inputs."""

from __future__ import annotations

import pytest

from harness.q1.mutate.native import InputSpec, NativeInputError, native_inputs
from tests._q1_mutate_support import RELU_PROBLEM

HINGE = """
import torch
batch_size = 32768
input_shape = (32768,)
dim = 1

def get_inputs():
    return [torch.rand(batch_size, *input_shape),
            torch.randint(0, 2, (batch_size,)).float() * 2 - 1]
"""

CONV = """
import torch
batch_size = 16
in_channels = 3
height = width = 256

def get_inputs():
    x = torch.randn(batch_size, in_channels, height, width)
    return [x]
"""


def test_relu_native_shape():
    assert native_inputs(RELU_PROBLEM) == [InputSpec("rand", (4096, 393216), False)]
    assert native_inputs(RELU_PROBLEM)[0].nonnegative_uniform


def test_starred_shapes_and_transformed_generators():
    specs = native_inputs(HINGE)
    assert specs[0] == InputSpec("rand", (32768, 32768), False)
    assert specs[1].generator == "randint" and specs[1].transformed
    assert specs[1].shape == (32768,)


def test_chained_module_assignment_and_local_names():
    assert native_inputs(CONV) == [InputSpec("randn", (16, 3, 256, 256), False)]


@pytest.mark.parametrize(
    "source",
    [
        "import torch\n",
        "import torch\ndef get_inputs():\n    return make()\n",
        "import torch\ndef get_inputs():\n    return [torch.rand(n)]\n",
    ],
)
def test_unreadable_problems_fail_closed(source):
    with pytest.raises(NativeInputError):
        native_inputs(source)
