from __future__ import annotations

import pytest

from harness.sparse_indexer_k1_marker import (
    MarkerError,
    read_checkpoint_marker,
    write_checkpoint_marker,
)


def batch_script_confirms(content: str, signal_name: str) -> bool:
    """The batch script's content test: a line exactly trigger=SIG<name>."""

    return f"\ntrigger=SIG{signal_name}\n" in f"\n{content}\n"


def test_marker_carries_the_trigger_line_and_round_trips(tmp_path) -> None:
    marker = tmp_path / "checkpoint.ready"
    write_checkpoint_marker(marker, "SIGUSR1", "tok", {"0": {"step": 25}})
    content = marker.read_text()
    assert batch_script_confirms(content, "USR1")
    assert not batch_script_confirms(content, "TERM")
    fields = read_checkpoint_marker(marker)
    assert fields["trigger"] == "SIGUSR1" and fields["token"] == "tok"
    assert fields["acks"] == {"0": {"step": 25}}


def test_marker_is_replaced_atomically_with_a_new_file_version(tmp_path) -> None:
    marker = tmp_path / "checkpoint.ready"
    marker.write_text("stale periodic marker\n")
    before = marker.stat().st_ino
    write_checkpoint_marker(marker, "SIGTERM", "tok", {})
    assert marker.stat().st_ino != before
    assert batch_script_confirms(marker.read_text(), "TERM")
    assert not list(tmp_path.glob("*.tmp-*"))


def test_marker_rejects_a_non_signal_trigger(tmp_path) -> None:
    with pytest.raises(MarkerError):
        write_checkpoint_marker(tmp_path / "m", "periodic", "tok", {})
