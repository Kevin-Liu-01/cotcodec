from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIVE_SOURCE = Path("/tmp/cotcodec-memory-audit.eRYVgA/past-bench")
PATCHER_PATH = PROJECT_ROOT / "infra/research/past-bench/apply_checkpoint_overlay.py"
CHECKPOINT_PATH = PROJECT_ROOT / "infra/research/past-bench/checkpoint_runtime.py"
SPEC = importlib.util.spec_from_file_location("past_checkpoint_overlay", PATCHER_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.skipif(not LIVE_SOURCE.is_dir(), reason="pinned PAST checkout unavailable")
def test_checkpoint_overlay_applies_once_to_exact_upstream(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "src/past_bench/runner").mkdir(parents=True)
    shutil.copy2(LIVE_SOURCE / "src/past_bench/cli.py", source / "src/past_bench/cli.py")
    receipt = MODULE.apply_overlay(source_root=source, checkpoint_module=CHECKPOINT_PATH)
    patched = (source / "src/past_bench/cli.py").read_text(encoding="utf-8")
    assert receipt["upstream_cli_sha256"] == MODULE.UPSTREAM_CLI_SHA256
    assert "--resume-checkpoint" in patched
    assert "CHECKPOINT_STOP" in patched
    assert "CheckpointStore" in patched
    assert (source / "src/past_bench/runner/cotcodec_checkpoint.py").read_bytes() == (
        CHECKPOINT_PATH.read_bytes()
    )
    compile(patched, str(source / "src/past_bench/cli.py"), "exec")

    with pytest.raises(MODULE.CheckpointOverlayError, match="upstream hash"):
        MODULE.apply_overlay(source_root=source, checkpoint_module=CHECKPOINT_PATH)


def test_checkpoint_overlay_rejects_unregistered_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "src/past_bench/runner").mkdir(parents=True)
    (source / "src/past_bench/cli.py").write_text("print('different')\n", encoding="utf-8")
    with pytest.raises(MODULE.CheckpointOverlayError, match="upstream hash"):
        MODULE.apply_overlay(source_root=source, checkpoint_module=CHECKPOINT_PATH)
