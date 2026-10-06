from __future__ import annotations

import pytest

from scripts.compile_mnemon_actor_job import (
    compile_manifest,
)
from scripts.validate_memory_portfolio import MemoryPortfolioError


def _compile(**overrides):
    values = {
        "image_id": "sha256:" + "1" * 64,
        "run_root": "/shared/cotcodec/mnemon-actor",
        "git_sha": "2" * 40,
        "source_sha256": "3" * 64,
        "model_cache_host": "/shared/cotcodec/models",
        "receipt_sha256": "4" * 64,
        "panel_host_path": "/shared/cotcodec/inputs/mnemon-panel.json",
    }
    values.update(overrides)
    return compile_manifest(**values)


def test_compile_mnemon_actor_job_rejects_killed_revision() -> None:
    with pytest.raises(MemoryPortfolioError, match="MNEMON_STATIC_ROUTING_KILLED"):
        _compile()


def test_compile_mnemon_actor_job_rejects_panel_drift() -> None:
    with pytest.raises(ValueError, match="panel identity differs"):
        _compile(panel_sha256="0" * 64)


def test_compile_mnemon_actor_job_rejects_resume_after_kill() -> None:
    with pytest.raises(MemoryPortfolioError, match="MNEMON_STATIC_ROUTING_KILLED"):
        _compile(
            resume_from_job_id="321",
            resume_subpath="mnemon-actor",
        )
