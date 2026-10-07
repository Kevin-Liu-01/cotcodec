from __future__ import annotations

import dataclasses

import pytest

from harness import sparse_indexer_data as sid
from scripts import build_sparse_indexer_k1_bundle as builder
from scripts.run_sparse_indexer_k1_doctor import ByteTokenizer, synthetic_sources, tiny_params
from scripts.submit_docker_research_job import LICENSE_RE


@pytest.fixture(scope="module")
def bundle() -> dict:
    return builder.assemble_bundle(synthetic_sources(), ByteTokenizer(), tiny_params())


def test_bundle_is_deterministic(bundle) -> None:
    again = builder.assemble_bundle(synthetic_sources(), ByteTokenizer(), tiny_params())
    assert sid.canonical_json_bytes(again) == sid.canonical_json_bytes(bundle)


def test_licence_and_split(bundle) -> None:
    assert bundle["license"] == "LicenseRef-cotcodec-k1-bundle-v1"
    assert LICENSE_RE.fullmatch(bundle["license"])
    split = bundle["split"]
    assert not set(split["audit"]) & set(split["development"])
    assert not set(split["audit"]) & set(split["primary"])


def test_crossed_design_puts_every_audit_question_in_every_pair(bundle) -> None:
    prompts = bundle["eval"]["prompts"]
    audit_questions = {(m["link"], m["question_number"]) for m in bundle["eval"]["context_meta"]
                       if m["partition"] == "audit" and m["kind"] == "needle"}
    main = [p for p in prompts if p["role"] == "main"]
    pairs = {p["pair"] for p in main}
    assert len(pairs) == 14
    families = {p["family_id"] for p in main}
    assert len(families) == 14 * len(audit_questions)
    assert {p["condition"] for p in main} == {"MN", "CX"}
    same = {p["pair"] for p in prompts if p["role"] == "same-script"}
    assert len(same) == 10


def test_english_needle_contexts_are_shared_across_pairs(bundle) -> None:
    prompts = [p for p in bundle["eval"]["prompts"] if p["role"] == "main"
               and p["pair"].startswith("en>") and p["condition"] == "MN"]
    by_question = {}
    for p in prompts:
        by_question.setdefault(p["family_id"].split("|", 2)[2], set()).add(
            (p["context_index"], p["query_index"]))
    assert all(len(units) == 1 for units in by_question.values())


def test_every_prompt_reads_only_its_partition(bundle) -> None:
    split = sid.split_from_bundle(bundle)
    for partition in ("audit", "development"):
        clusters = [p["cluster"] for p in bundle["eval"]["prompts"]
                    if p["partition"] == partition]
        sid.check_partition_read(bundle, partition, clusters)
    assert not any(p["cluster"] in split.primary for p in bundle["eval"]["prompts"])


def test_prompt_layout_and_counts(bundle) -> None:
    view = sid.eval_view(bundle, ["audit", "development"], sid.split_from_bundle(bundle))
    roles = bundle["eval"]["counts"]["by_role"]
    params = tiny_params()
    assert roles["literal"] == params.ml_en + params.ml_x
    assert roles["absent"] == params.absent
    for prompt in view.prompts:
        tokens, q0, q1, n0, n1 = view.prompt_tokens(prompt)
        assert q0 < q1 <= len(tokens)
        if n0 >= 0:
            assert n1 <= q0


def test_filters_and_dedup_are_counted(bundle) -> None:
    dedup = bundle["reports"]["dedup"]
    assert dedup["bi-en-th"]["removed_held_out_script"] == 1
    assert dedup["bi-en-de"]["removed_held_out_latin_function_words"] == 1
    assert bundle["stream"]["train_tokens"]["shape"] == [12, 64]
    assert bundle["stream"]["dev_tokens"]["shape"] == [4, 64]


def test_cross_script_shortfall_is_refilled_from_same_script_pairs() -> None:
    sources = synthetic_sources()
    sources.bilingual["en-km"] = []
    bundle = builder.assemble_bundle(sources, ByteTokenizer(), tiny_params())
    quota = bundle["reports"]["quota"]["bilingual"]
    assert quota["cross_script_shortfall"] > 0
    assert quota["same_script_refill_quota"] > quota["pair_quota"]
    assert quota["collected_tokens"]["en-km"] == 0
    assert quota["packed_tokens_by_pair"]["en-km"] == 0
    assert sum(quota["packed_share_by_pair"].values()) == pytest.approx(1.0)


def test_write_bundle_refuses_overwrite_and_oversize(tmp_path, bundle) -> None:
    path = tmp_path / "b.json"
    summary = builder.write_bundle(bundle, path, 64 * 1024**2)
    assert summary["sha256"] == sid.sha256_file(path)
    with pytest.raises(sid.DataContractError, match="exists"):
        builder.write_bundle(bundle, path, 64 * 1024**2)
    with pytest.raises(sid.DataContractError, match="above"):
        builder.write_bundle(bundle, tmp_path / "c.json", 10)


def test_registered_params_and_sources() -> None:
    params = builder.BuildParams()
    assert params.bilingual_train + params.mono_train == 2441
    assert params.bilingual_dev + params.mono_dev == 64
    assert params.pair_quota == 1253 * 8191 // 7
    assert sid.PARADOCS_SOURCE["en-km"] == "all/paracrawl"
    assert sid.PARADOCS_SOURCE["en-de"] == "strict"
    assert dataclasses.replace(params, haystack_docs=1).haystack_docs == 1


def test_main_maps_contract_errors_to_exit_two(tmp_path, monkeypatch) -> None:
    def fail(_args):
        raise sid.DataContractError("raw file changed")

    monkeypatch.setattr(builder, "cmd_build", fail)
    code = builder.main(["build", "--raw-dir", str(tmp_path), "--model-dir", str(tmp_path),
                         "--output", str(tmp_path / "x.json"), "--git-sha", "0" * 40])
    assert code == 2


def test_parquet_reader(tmp_path) -> None:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    table = pa.table({"id": ["a", "b"], "text": ["x", "y"], "other": [1, 2]})
    pq.write_table(table, tmp_path / "t.parquet")
    assert builder._parquet_texts(tmp_path / "t.parquet") == [("a", "x"), ("b", "y")]
