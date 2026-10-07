"""Pinned upstream sources for the Q1 substrate corpus and the problem exclusion list.

Every substrate records ``source_repo``, ``source_revision`` and
``source_license`` from :data:`SOURCES`. Licences were read from the LICENSE
file at the pinned revision on 2026-10-06 (FlagGems and Liger on the host
clones; Triton from the tutorials' repository root at the pinned commit).
"""

from __future__ import annotations

from dataclasses import dataclass

from harness.q1.schema import KERNELBENCH_PROBLEMS_REVISION, parse_problem_id


@dataclass(frozen=True)
class UpstreamSource:
    key: str
    source_kind: str
    repo: str
    revision: str
    tag: str | None
    license: str
    license_file: str
    notice_file: str | None
    note: str


SOURCES: dict[str, UpstreamSource] = {
    "kernelbench": UpstreamSource(
        key="kernelbench",
        source_kind="problems",
        repo="https://github.com/ScalingIntelligence/KernelBench",
        revision=KERNELBENCH_PROBLEMS_REVISION,
        tag=None,
        license="MIT",
        license_file="LICENSE",
        notice_file=None,
        note="Problem definitions (Model, get_inputs, get_init_inputs), commit 2026-03-05.",
    ),
    "flaggems": UpstreamSource(
        key="flaggems",
        source_kind="flaggems",
        repo="https://github.com/flagos-ai/FlagGems",
        revision="18b8e4281610c91e178518271bc756a98fdc84c9",
        tag="v1.0-manual",
        license="Apache-2.0",
        license_file="LICENSE",
        notice_file=None,
        note="Hand-written Triton operators, tag v1.0-manual (2024-04-25). No NOTICE file "
        "exists at the tag; the LICENSE header reads 'Copyright (c) 2024 BAAI'.",
    ),
    "liger": UpstreamSource(
        key="liger",
        source_kind="liger",
        repo="https://github.com/linkedin/Liger-Kernel",
        revision="1520999e60e34a9e034026d05917082de098be1e",
        tag="v0.3.1",
        license="BSD-2-Clause",
        license_file="LICENSE",
        notice_file="NOTICE",
        note="Hand-written Triton kernels, tag v0.3.1 (2024-10-01). Copyright 2024 LinkedIn "
        "Corporation; NOTICE kept.",
    ),
    "triton-tutorials": UpstreamSource(
        key="triton-tutorials",
        source_kind="triton-tutorial",
        repo="https://github.com/triton-lang/triton",
        revision="105cb56487cd8a433b8fbfe9cc63c1f1c04a4b2a",
        tag=None,
        license="MIT",
        license_file="LICENSE",
        notice_file=None,
        note="python/tutorials at a 2024-12-09 commit (pre-2025).",
    ),
    "pytorch": UpstreamSource(
        key="pytorch",
        source_kind="inductor",
        repo="https://github.com/pytorch/pytorch",
        # torch 2.11.0+cu128 in cotcodec-research:0b3ecef0-architecture; the build
        # step reads torch.version.git_version and refuses a mismatch.
        revision="70d99e998b4955e0049d13a98d77ae1b14db1f45",
        tag="v2.11.0",
        license="BSD-3-Clause",
        license_file="LICENSE",
        notice_file="NOTICE",
        note="TorchInductor code generator; generated kernels embed Inductor templates and "
        "call torch._inductor.runtime.triton_helpers.",
    ),
}

#: Problems excluded before any substrate is built (reviewed plan, section 7(i)).
#: Further exclusions come only from admission, never by hand.
EXCLUDED_PROBLEMS: dict[str, str] = {
    "L2/23_Conv3d_GroupNorm_Mean": "constant-zero output (KernelBench-Verified App. I)",
    "L2/80_Gemm_Max_Subtract_GELU": "constant-zero output (KernelBench-Verified App. I)",
    "L2/83_Conv3d_GroupNorm_Min_Clamp_Dropout": "constant-zero output (KernelBench-Verified "
    "App. I)",
    "L2/66_Matmul_Dropout_Softmax": "training-mode Dropout(p=0.2): the reference is random",
}

#: Levels in the Stage 0 corpus.
LEVELS = (1, 2)


def is_admissible_problem(problem_id: str) -> bool:
    """True when ``problem_id`` is an L1/L2 problem not on the exclusion list."""
    level, _, _ = parse_problem_id(problem_id)
    return level in LEVELS and problem_id not in EXCLUDED_PROBLEMS


def source(key: str) -> UpstreamSource:
    try:
        return SOURCES[key]
    except KeyError as exc:
        raise KeyError(f"unknown upstream source {key!r}; known: {sorted(SOURCES)}") from exc
