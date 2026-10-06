import pytest

from scripts.compile_memorybank_h100_jobs import compile_manifests
from scripts.validate_memory_portfolio import MemoryPortfolioError


def test_compile_memorybank_h100_jobs_rejects_killed_revision() -> None:
    with pytest.raises(
        MemoryPortfolioError,
        match="MEMORYBANK_CORRECTED_DECAY_PASS_NO_DECAY_KILLS_SCALING",
    ):
        compile_manifests(
            image_id="sha256:" + "a" * 64,
            run_root="/home/kevin/cotcodec-runs",
            git_sha="b" * 40,
            source_sha256="c" * 64,
            model_cache_host="/home/kevin/cotcodec-runs/hf-cache",
            receipt_sha256="d" * 64,
            remote_bundle_root="/home/kevin/cotcodec-inputs/memorybank",
        )


def test_compile_memorybank_h100_resume_rejects_killed_revision() -> None:
    with pytest.raises(
        MemoryPortfolioError,
        match="MEMORYBANK_CORRECTED_DECAY_PASS_NO_DECAY_KILLS_SCALING",
    ):
        compile_manifests(
            image_id="sha256:" + "a" * 64,
            run_root="/home/kevin/cotcodec-runs/memorybank-resume",
            git_sha="b" * 40,
            source_sha256="c" * 64,
            model_cache_host="/home/kevin/cotcodec-runs/hf-cache",
            receipt_sha256="d" * 64,
            remote_bundle_root="/home/kevin/cotcodec-inputs/memorybank",
            resume_from_job_ids={"no_decay": 330},
        )
