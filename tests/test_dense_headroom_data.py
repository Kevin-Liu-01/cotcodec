"""Inputs of the dense headroom pre-check: codecs, the development artifact, features, units."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import numpy as np
import pytest
import yaml

from harness import dense_headroom_data as dhd
from harness import sparse_indexer_data as sid
from harness.translation_supervised_indexer import IndexerContractError
from scripts import run_dense_headroom_precheck_doctor as doctor

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bundle(tmp_path_factory) -> dict:
    path, _ = doctor.build_tiny_bundle(tmp_path_factory.mktemp("bundle"))
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def artifacts(bundle) -> dict[str, dict]:
    return {lane: dhd.derive_dev_artifact(copy.deepcopy(bundle), *doctor.tiny_codecs(lane),
                                          dhd.lane_of(lane))
            for lane in ("tiny-attention", "tiny-hybrid")}


def test_stand_in_codecs_round_trip_and_differ() -> None:
    byte, pair = dhd.StandInByteCodec(), dhd.StandInPairCodec()
    for text in ("hello world", "naïve café", "日本語", "a\n\nb 1990"):
        assert byte.decode_bytes(byte.encode(text)).decode() == text
        assert pair.decode_bytes(pair.encode(text)).decode() == text
    assert len(pair.encode("abcd")) == 2 and len(byte.encode("abcd")) == 4
    assert byte.sink == 1 and pair.sink == 2


def test_decode_text_drops_only_an_incomplete_haystack_tail() -> None:
    codec = dhd.StandInByteCodec()
    cut = codec.encode("xé")[:-1]
    assert dhd.decode_text(codec, cut, tail_tolerant=True) == ("x", 1)
    with pytest.raises(dhd.DenseDataError):
        dhd.decode_text(codec, cut)
    broken = codec.encode("x") + [2 + 0xFF] + codec.encode("y")
    with pytest.raises(dhd.DenseDataError):
        dhd.decode_text(codec, broken, tail_tolerant=True)


def test_byte_level_codec_is_byte_exact(tmp_path) -> None:
    tokenizers = pytest.importorskip("tokenizers")
    vocab = {c: i for i, c in enumerate(dhd._bytes_to_unicode().values())}
    tok = tokenizers.Tokenizer(tokenizers.models.BPE(vocab=vocab, merges=[]))
    tok.pre_tokenizer = tokenizers.pre_tokenizers.ByteLevel(add_prefix_space=False,
                                                            use_regex=False)
    tok.add_special_tokens(["<|endoftext|>"])
    tok.save(str(tmp_path / "tokenizer.json"))
    codec = dhd.ByteLevelCodec(tmp_path / "tokenizer.json")
    for text in ("Ελληνικά 1990", "বাংলা ১৯৯০", "x\n\ny"):
        assert codec.decode_bytes(codec.encode(text)).decode() == text
    with pytest.raises(dhd.DenseDataError):
        codec.decode_bytes([codec.sink])


def test_english_anchors_and_digits() -> None:
    assert dhd.english_anchors("When did Alice's team reach Kyoto in 1990?",
                               "Alice and her team reached Kyoto in 1990.") == {
        "capitalised": ["Alice", "Kyoto"], "digits": ["1990"]}
    assert dhd.english_anchors("Who wrote it?", "Who knows.") == {"capitalised": [],
                                                                 "digits": []}
    assert dhd.english_anchors("Did I see Paris?", "I saw Rome.") == {"capitalised": [],
                                                                     "digits": []}
    assert dhd.digit_runs("১৯৯০, ٢٠٢٠ and 7") == {"1990", "2020", "7"}


def test_budget_is_twelve_and_a_half_percent() -> None:
    assert dhd.budget_blocks(8192) == 256 == dhd.FIXED_BLOCK_BUDGET
    assert dhd.budget_blocks(6000) == 187
    assert dhd.budget_blocks(128) == 4 == dhd.fixed_blocks("tiny")
    with pytest.raises(dhd.DenseDataError):
        dhd.budget_blocks(3)


def test_identity_lane_keeps_the_bundles_tokens(bundle, artifacts) -> None:
    artifact = artifacts["tiny-attention"]
    view = dhd.DevView(artifact)
    section = bundle["eval"]
    tokens = sid.decode_array(section["context_tokens"])
    offsets = sid.decode_array(section["context_offsets"])
    for index, meta in enumerate(view.contexts):
        source = tokens[offsets[meta["source_index"]] : offsets[meta["source_index"] + 1]]
        assert np.array_equal(source, view.context(index))
        assert meta["source_tokens_sha256"] == meta["tokens_sha256"]
    assert not artifact["retokenized"]


def test_retokenized_lane_keeps_every_needle_exact(bundle, artifacts) -> None:
    artifact = artifacts["tiny-hybrid"]
    view = dhd.DevView(artifact)
    source, codec = doctor.tiny_codecs("tiny-hybrid")
    section = bundle["eval"]
    tokens = sid.decode_array(section["context_tokens"])
    offsets = sid.decode_array(section["context_offsets"])
    lengths_changed = 0
    for index, meta in enumerate(view.contexts):
        mine = view.context(index)
        assert int(mine[0]) == codec.sink
        src_meta = section["context_meta"][meta["source_index"]]
        src = tokens[offsets[meta["source_index"]] : offsets[meta["source_index"] + 1]]
        lengths_changed += len(src) != len(mine)
        if meta["kind"] == "absent":
            assert meta["needle_start"] == meta["needle_end"] == -1
            continue
        assert (codec.decode_bytes(mine[meta["needle_start"] : meta["needle_end"]])
                == source.decode_bytes(src[src_meta["needle_start"] : src_meta["needle_end"]]))
    assert lengths_changed == len(view.contexts)
    for query in view.queries:
        if query["kind"] == "question":
            assert len(query["options"]) == 4


def test_artifact_is_deterministic_and_has_the_literal_prompts(bundle, artifacts) -> None:
    for lane, artifact in artifacts.items():
        again = dhd.derive_dev_artifact(copy.deepcopy(bundle), *doctor.tiny_codecs(lane),
                                        dhd.lane_of(lane))
        assert dhd.artifact_sha256(again) == dhd.artifact_sha256(artifact)
        view = dhd.DevView(artifact)
        literal = [p for p in view.prompts if p["role"] == dhd.LITERAL_ROLE]
        questions = {(p["cluster"], p["question_number"]) for p in view.prompts}
        assert len(literal) == 8 * len(questions)
        codec = doctor.tiny_codecs(lane)[1]
        for prompt in literal:
            tokens, q0, q1, n0, n1 = view.unit_tokens(prompt["context_index"],
                                                      prompt["query_index"])
            assert codec.decode_bytes(tokens[q0:q1]) in codec.decode_bytes(tokens[n0:n1])
            assert n1 <= q0


@pytest.mark.parametrize("target", ["prompt", "context", "query"])
def test_reads_outside_the_development_partition_fail_closed(bundle, target) -> None:
    tampered = copy.deepcopy(bundle)
    first = next(i for i, p in enumerate(tampered["eval"]["prompts"])
                 if p["partition"] == "development" and p["role"] == "dev")
    prompt = tampered["eval"]["prompts"][first]
    audit_link = tampered["split"]["audit"][0]
    if target == "prompt":
        prompt["cluster"] = audit_link
    elif target == "context":
        tampered["eval"]["context_meta"][prompt["context_index"]]["partition"] = "audit"
    else:
        tampered["eval"]["query_meta"][prompt["query_index"]]["link"] = audit_link
    with pytest.raises((dhd.DenseDataError, IndexerContractError)):
        dhd.derive_dev_artifact(tampered, *doctor.tiny_codecs("tiny-attention"),
                                dhd.lane_of("tiny-attention"))


def test_registered_lanes_refuse_other_role_counts_and_tokenizers(bundle) -> None:
    source, _ = doctor.tiny_codecs("tiny-attention")
    with pytest.raises(dhd.DenseDataError, match="role counts"):
        dhd.derive_dev_artifact(copy.deepcopy(bundle), source, source,
                                dhd.lane_of("qwen3-0.6b-base"))
    with pytest.raises(dhd.DenseDataError, match="bundle's tokenizer"):
        dhd.derive_dev_artifact(copy.deepcopy(bundle), dhd.StandInPairCodec(), source,
                                dhd.lane_of("tiny-attention"))
    with pytest.raises(dhd.DenseDataError, match="without re-tokenization"):
        dhd.derive_dev_artifact(copy.deepcopy(bundle), source, dhd.StandInPairCodec(),
                                dhd.lane_of("tiny-attention"))


def test_units_are_unique_and_staged(artifacts) -> None:
    view = dhd.DevView(artifacts["tiny-attention"])
    units = dhd.plan_units(view.prompts)
    questions = len({(p["cluster"], p["question_number"]) for p in view.prompts})
    assert len(units) == len({u.unit_id for u in units}) == 58 * questions
    stages = [dhd.STAGES.index(u.stage) for u in units]
    assert stages == sorted(stages)
    by_stage = {s: [u for u in units if u.stage == s] for s in dhd.STAGES}
    assert len(by_stage["A-main"]) == 22 * questions
    assert all(u.select and u.mc for u in by_stage["A-main"])
    assert all(u.mc and not u.select for u in by_stage["B-absent"] + by_stage["D-nohaystack"])
    assert all(u.select and not u.mc for u in by_stage["C-literal"])
    for prompt in view.prompts:
        assert dhd.unit_of(prompt) in {u.unit_id for u in units}


def test_k1_smoke_units_follow_k1_v1s_order(bundle, artifacts) -> None:
    prompts = [p for p in bundle["eval"]["prompts"] if p["partition"] == "development"]
    keys = sorted({f"c{p['context_index']}-q{p['query_index']}" for p in prompts
                   if p["role"] == "dev"})
    assert dhd.k1_smoke_units(prompts) == keys[:20]
    assert artifacts["tiny-attention"]["source"]["k1_smoke_units"] == keys[:20]


def test_k1_smoke_units_equal_k1_runtime_plan_units(bundle) -> None:
    pytest.importorskip("torch")
    from harness import sparse_indexer_k1_runtime as rt

    prompts = [p for p in bundle["eval"]["prompts"] if p["partition"] == "development"]
    units, _ = rt.plan_units(prompts, {"dev"}, set(), set())
    expected = [u["unit"] for u in units if u["select"]][:20]
    assert dhd.k1_smoke_units(prompts) == expected


def test_lexical_scores_count_context_content_tokens() -> None:
    codec = dhd.StandInByteCodec()
    content = dhd.ContentFilter(codec, {"en": codec.encode("e")})
    context = [codec.sink] + codec.encode("abcd xyz cab ")  # 14 tokens
    query = codec.encode("\n\ncab?\n")
    tokens = np.asarray(context + query, dtype=np.uint32)
    q0, q1 = len(context) + 2, len(context) + 6
    scores = dhd.lexical_block_scores(tokens, len(context), q0, q1, "en", content)
    # Content ids of "cab?": c, a, b ("?" is symbol-only). Context blocks:
    # [sink a b c] [d ' ' x y] [z ' ' c a] [b ' ' ...] -> 3, 0, 2, 1.
    assert scores[:4].tolist() == [3.0, 0.0, 2.0, 1.0]
    assert scores[len(context) // 4 + 1 :].sum() == 0


def test_stop_ids_tie_break_to_the_lower_id() -> None:
    contexts = [{"kind": "absent", "needle_language": "en", "needle_start": -1,
                 "needle_end": -1}]
    tokens = np.asarray([1, 9, 9, 5, 5, 7], dtype=np.uint32)
    assert dhd.stop_ids_by_language(contexts, lambda _: tokens, limit=2) == {"en": [5, 9]}


def test_registered_lanes_and_caps() -> None:
    assert dhd.registered_caps_total() == dhd.TOTAL_CAP_GPU_HOURS == 0.5
    for lane in dhd.LANES.values():
        assert lane.gpus * lane.minutes / 60 == pytest.approx(lane.cap_gpu_hours)
    v1 = (PROJECT_ROOT / "program" / "preregistrations"
          / "q3-k1-localization-screen-v1.md").read_text(encoding="utf-8")
    small = dhd.LANES["qwen3-0.6b-base"]
    for value in (small.revision, small.receipt_sha256, small.artifact_root_sha256,
                  small.tokenizer_sha256, dhd.SOURCE_BUNDLE_SHA256):
        assert value in v1
    registry = yaml.safe_load((PROJECT_ROOT / "models" / "registry.yaml").read_text())
    for lane in dhd.LANES.values():
        assert registry["models"][lane.model_id]["revision"] == lane.revision
    assert dhd.LANES["qwen3.5-4b-base"].attention_layers == tuple(range(3, 32, 4))
    assert all(re.fullmatch(r"[0-9a-f]{64}", lane.receipt_sha256) for lane in dhd.LANES.values())
