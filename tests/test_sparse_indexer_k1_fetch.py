from __future__ import annotations

import gzip
import json

import pytest

from harness import sparse_indexer_data as sid
from scripts import build_sparse_indexer_k1_bundle as builder
from scripts.run_sparse_indexer_k1_doctor import ByteTokenizer


def tsv_line(src: str, tgt: str, start: int, docid: str = "d") -> str:
    fields = [src, tgt, "1", "1", "c", "1", "1", "1", "1", str(start), str(start + 3),
              str(start), str(start + 3), "0.9", "0.9", "1", docid, docid]
    return "\t".join(fields) + "\n"


@pytest.fixture
def offline(monkeypatch):
    lines = []
    for doc in range(40):
        long_side = "x" * (600 if doc == 0 else 10)
        lines.append(tsv_line(long_side, "y" * 10, 0, f"doc{doc}"))
        lines.append(tsv_line("a" * 10, "b" * 10, 4, f"doc{doc}"))
    payload = gzip.compress("".join(lines).encode())
    files = [{"path": "data/en-th/all/paracrawl/000.gz", "size": len(payload),
              "lfs_sha256": None}]
    monkeypatch.setattr(builder, "_paradocs_files", lambda pair: files)
    monkeypatch.setattr(builder, "_stream_chunks", lambda url, max_bytes: iter(
        [payload[i : i + 7] for i in range(0, len(payload), 7)]))
    monkeypatch.setattr(builder, "Tokenizer", lambda path: ByteTokenizer())
    return payload


def test_stream_counts_tokens_with_the_builder_side_cap(offline) -> None:
    record = builder.stream_paradocs_pair("en-th", ByteTokenizer(), token_quota=None,
                                          max_bytes=10**9, cfg=sid.ParadocsFilter())
    assert record["kept_documents"] == 40
    # doc 0's English side has 611 byte tokens; only 512 count toward the quota.
    separators = 40 * 2
    uncapped = record["kept_en_tokens"] + record["kept_x_tokens"] + separators
    assert uncapped - record["kept_item_tokens"] == 611 - builder.BILINGUAL_SIDE_MAX_TOKENS
    assert record["stop_reason"] == "files-ended"
    assert record["bytes_consumed"] == len(offline)


def test_fetch_pair_is_deterministic_and_resumable(offline, tmp_path) -> None:
    for name in ("a", "b"):
        (tmp_path / name / "paradocs").mkdir(parents=True)
    first = builder._fetch_pair("en-th", str(tmp_path / "a"), "unused", 10**9, 10**9)
    second_root = tmp_path / "b"
    second = builder._fetch_pair("en-th", str(second_root), "unused", 10**9, 10**9)
    assert first["filtered_file_sha256"] == second["filtered_file_sha256"]
    assert first["stop_reason"] == "files-ended"
    assert first["source_folder"] == "all/paracrawl"
    with gzip.open(second_root / "paradocs" / "en-th.jsonl.gz", "rt", encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    assert len(rows) == 40 and rows[0]["doc_id"].startswith("en-th:000.gz:0:")
    again = builder._fetch_pair("en-th", str(second_root), "unused", 10**9, 10**9)
    assert again == second
    (second_root / "paradocs" / "en-th.jsonl.gz").write_bytes(b"tampered")
    with pytest.raises(sid.DataContractError):
        builder._fetch_pair("en-th", str(second_root), "unused", 10**9, 10**9)


def test_byte_cap_inside_a_gzip_member_stops_cleanly(offline, monkeypatch) -> None:
    monkeypatch.setattr(builder, "_stream_chunks",
                        lambda url, max_bytes: iter([offline[: len(offline) // 2]]))
    record = builder.stream_paradocs_pair("en-th", ByteTokenizer(), token_quota=None,
                                          max_bytes=len(offline) // 2, cfg=sid.ParadocsFilter())
    assert record["bytes_consumed"] == len(offline) // 2
    assert record["kept_documents"] <= 40
