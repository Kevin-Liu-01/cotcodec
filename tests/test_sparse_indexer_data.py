from __future__ import annotations

import gzip
import io
import json

import numpy as np
import pytest

from harness import sparse_indexer_data as sid
from harness.translation_supervised_indexer import IndexerContractError

BASE = {"similarity_one": "1", "similarity_two": "1", "collection": "c",
        "src_paragraph_id": "1", "tgt_paragraph_id": "1", "src_sentence_id": "1",
        "tgt_sentence_id": "1", "src_language_id": "0.9", "tgt_language_id": "0.9",
        "frequency": "1", "src_docid": "d", "tgt_docid": "e"}


def line(src: str, s0: int, s1: int, t0: int, t1: int, **over: str) -> dict:
    return {**BASE, "src": src, "tgt": src.upper(), "src_start_index": str(s0),
            "src_end_index": str(s1), "tgt_start_index": str(t0), "tgt_end_index": str(t1),
            **over}


def kept(rows, **cfg) -> list[list[str]]:
    docs = sid.paradocs_documents(rows, sid.ParadocsFilter(**cfg))
    return [[row["src"] for row in doc] for doc in docs]


def test_paradocs_target_side_quirk_is_replicated() -> None:
    rows = [line("a", 0, 5, 0, 5), line("b", 6, 9, 500, 505)]
    assert kept(rows) == [["a", "b"]]


def test_paradocs_source_gap_splits_and_minimum_size_drops() -> None:
    rows = [line("a", 0, 5, 0, 5), line("b", 6, 9, 6, 9), line("c", 40, 45, 40, 45)]
    assert kept(rows) == [["a", "b"]]
    assert kept(rows, minimum_size=1) == [["a", "b"], ["c"]]


@pytest.mark.parametrize("override", [{"frequency": "101"}, {"src_language_id": "0.4"},
                                      {"tgt_language_id": "0.1"}, {"src_sentence_id": "None"},
                                      {"tgt": "  "}, {"frequency": "abc"}])
def test_paradocs_breaks_end_a_document(override) -> None:
    rows = [line("a", 0, 5, 0, 5), line("b", 6, 9, 6, 9), line("x", 10, 12, 10, 12, **override),
            line("c", 13, 15, 13, 15), line("d", 16, 18, 16, 18)]
    assert kept(rows) == [["a", "b"], ["c", "d"]]


def test_paradocs_new_document_id_starts_a_new_document() -> None:
    rows = [line("a", 0, 5, 0, 5), line("b", 6, 9, 6, 9),
            line("c", 10, 12, 10, 12, src_docid="other"),
            line("d", 13, 15, 13, 15, src_docid="other")]
    assert kept(rows) == [["a", "b"], ["c", "d"]]


def test_paradocs_rows_and_gzip_reader_count_bytes() -> None:
    text = "\t".join(["he said \"hi\"", "x"] + ["1"] * 16) + "\n"
    payload = gzip.compress(text.encode()) + gzip.compress(text.encode())
    reader = sid.CountingReader(iter([payload[:10], payload[10:]]))
    rows = list(sid.paradocs_rows(sid.gzip_text_lines(reader)))
    assert len(rows) == 2 and rows[0]["src"] == 'he said "hi"'
    assert reader.consumed == len(payload)


def test_script_and_latin_filters() -> None:
    assert sid.held_out_script_fraction("ab αβ") == pytest.approx(0.5)
    assert not sid.passes_script_filter("x" * 100 + "가")
    assert sid.passes_script_filter("x" * 300 + "가")
    assert sid.passes_script_filter("中文 kanji are allowed")
    assert sid.reads_as_held_out_latin("het een niet zijn voor", "de")
    assert not sid.reads_as_held_out_latin("le les des et est", "fr")


def test_window_hashes_match_naive_tuples() -> None:
    tokens = [5, 9, 5, 9, 5, 7]
    hashes = sid.window_hashes(tokens, 2)
    windows = [tuple(tokens[i : i + 2]) for i in range(5)]
    assert (hashes[0] == hashes[2]) and (windows[0] == windows[2])
    assert len(set(hashes.tolist())) == len(set(windows))
    assert sid.window_hashes([1, 2], 5).size == 0


def test_dedup_index_exact_near_and_clean() -> None:
    evaluation = list(range(1000, 1080))
    index = sid.DedupIndex([evaluation, [7, 8]])
    stats = sid.DedupStats()
    assert not index.check([1] + evaluation[10:62] + [2], stats)
    assert stats.exact_ngram == 1
    near = evaluation[:40] + [5] + evaluation[41:]
    assert index.max_jaccard(near) >= sid.MINHASH_THRESHOLD
    assert index.check(list(range(3000, 3100)), stats)


def test_pack_sequences_layout_and_exhaustion() -> None:
    packed, used = sid.pack_sequences([[5, 6, 7], [8, 9], [10, 11, 12, 13], [14]], 2, length=6,
                                      sink=1)
    assert packed.tolist() == [[1, 5, 6, 7, 1, 8], [1, 10, 11, 12, 13, 1]]
    assert used == 4
    with pytest.raises(sid.DataContractError):
        sid.pack_sequences([[5]], 2, length=6, sink=1)


def test_build_context_places_needle_at_nearest_boundary() -> None:
    hay = [(f"d{i}", [10 + i] * 9) for i in range(6)]
    context = sid.build_context([90, 91], hay, 0.5, [3], length=40, sink=1)
    assert len(context.tokens) == 40 and context.tokens[0] == 1
    assert context.tokens[context.needle_start : context.needle_end].tolist() == [90, 91]
    assert context.tokens[context.needle_start - 1] == 3  # follows a document separator
    early = sid.build_context([90, 91], hay, 0.0, [3], length=40, sink=1)
    assert early.needle_start == 1
    absent = sid.build_context(None, hay, 0.5, [3], length=40, sink=1)
    assert absent.needle_start == -1 and 90 not in absent.tokens.tolist()
    with pytest.raises(sid.DataContractError):
        sid.build_context([90], hay[:1], 0.5, [3], length=40, sink=1)


def row(link: str, q: int, correct: int, text: str = "t") -> sid.BelebeleRow:
    return sid.BelebeleRow(link, q, text, text + "?", ("a", "b", "c", "d"), correct)


def test_belebele_join_is_keyed_not_ordered() -> None:
    en = [row("l1", 1, 2), row("l2", 1, 3)]
    ja = [row("l2", 1, 3, "j"), row("l1", 1, 2, "j")]
    joined = sid.belebele_join({"en": en, "ja": ja})
    assert joined[("l1", 1)]["ja"].passage == "j"
    with pytest.raises(sid.DataContractError, match="answer key"):
        sid.belebele_join({"en": en, "ja": [row("l2", 1, 1), row("l1", 1, 2)]})
    with pytest.raises(sid.DataContractError, match="missing"):
        sid.belebele_join({"en": en, "ja": ja[:1]})


def test_parse_belebele_line_rejects_bad_answer() -> None:
    payload = {"link": "l", "question_number": 1, "flores_passage": "p", "question": "q",
               "mc_answer1": "a", "mc_answer2": "b", "mc_answer3": "c", "mc_answer4": "d",
               "correct_answer_num": "5"}
    with pytest.raises(sid.DataContractError):
        sid.parse_belebele_line(json.dumps(payload))


def test_codec_round_trip_and_digest() -> None:
    array = np.arange(12, dtype=np.uint32).reshape(3, 4)
    encoded = sid.encode_array(array)
    assert np.array_equal(sid.decode_array(encoded), array)
    with pytest.raises(sid.DataContractError):
        sid.decode_array({**encoded, "sha256": "0" * 64})


def test_load_bundle_checks_digest_before_parsing(tmp_path) -> None:
    path = tmp_path / "b.json"
    path.write_bytes(sid.canonical_json_bytes({"schema": sid.BUNDLE_SCHEMA}))
    with pytest.raises(sid.DataContractError, match="sha256"):
        sid.load_bundle(path, "0" * 64)
    assert sid.load_bundle(path, sid.sha256_file(path))["schema"] == sid.BUNDLE_SCHEMA


def test_partition_reads_fail_closed() -> None:
    bundle = {"split": {"seed": 42, "development": ["a"], "audit": ["b"], "primary": ["c"]}}
    sid.check_partition_read(bundle, "audit", ["b"])
    with pytest.raises(IndexerContractError):
        sid.check_partition_read(bundle, "audit", ["b", "c"])


def test_sentence_split_handles_cjk_and_danda() -> None:
    assert sid.split_sentences("One. Two? Three!") == ["One.", "Two?", "Three!"]
    assert sid.split_sentences("一つ。二つ。") == ["一つ。", "二つ。"]
    assert sid.split_sentences("এক। দুই।") == ["এক।", "দুই।"]


def test_counting_reader_is_a_binary_stream() -> None:
    reader = sid.CountingReader(iter([b"abc", b"de"]))
    assert io.BufferedReader(reader).read() == b"abcde"
