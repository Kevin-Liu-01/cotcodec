"""Pool -> select -> layout, compile filtering, hack controls and the CLI."""

from __future__ import annotations

import ast
import json

import pytest

from harness.q1.mutate import corpus
from harness.q1.mutate.compiled import compiled_key, launch_scope_hash
from harness.q1.mutate.fixtures import HACK_KINDS, build_hack_control
from harness.q1.schema import load_kernel_dir, sha256_file
from scripts import q1_generate_mutants as cli
from tests._q1_mutate_support import (
    RELU_PROBLEM,
    make_kernelbench,
    make_substrates,
    substrate_record,
    toy_text,
)

CORPUS_TOYS = ["relu_where", "matmul", "softmax_rows"]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("corpus")
    substrates = make_substrates(root / "substrates", CORPUS_TOYS)
    corpus.build_pool(substrates, root / "pool")
    corpus.select(
        root / "pool",
        substrates,
        root / "mutants",
        require_compile=False,
        controls_root=root / "mutant-controls",
    )
    return root


def test_mutant_layout_validates_against_the_shared_schema(built):
    mutants_root = built / "mutants"
    rows = [json.loads(x) for x in (mutants_root / "mutants.jsonl").read_text().splitlines()]
    assert rows
    for row in rows:
        kernel = load_kernel_dir(mutants_root / row["mutant_id"])
        assert kernel.kind == "mutant"
        parent = built / "substrates" / row["parent_substrate_id"]
        assert sha256_file(kernel.path / "substrate.json") == sha256_file(parent / "substrate.json")
        assert kernel.mutation["seed"] == 42
        assert kernel.mutation["dedup_hash"] == row["dedup_hash"]
        ast.parse(kernel.kernel_path.read_text())
        assert row["split"] in {"dev", "test"}


def test_cap_and_manifest_totals(built):
    manifest = json.loads((built / "mutants" / "manifest.json").read_text())
    assert manifest["compile_checked"] is False
    assert manifest["cap"] == 40 and manifest["seed"] == 42
    for summary in manifest["substrates"]:
        assert summary["selected"] == min(40, summary["eligible"])
    rows = (built / "mutants" / "mutants.jsonl").read_text().splitlines()
    assert manifest["totals"]["selected"] == len(rows)
    assert manifest["mutants_sha256"] == sha256_file(built / "mutants" / "mutants.jsonl")


def test_pipeline_is_byte_deterministic(built, tmp_path):
    substrates = make_substrates(tmp_path / "substrates", CORPUS_TOYS)
    corpus.build_pool(substrates, tmp_path / "pool")
    corpus.select(tmp_path / "pool", substrates, tmp_path / "mutants", require_compile=False)
    for name in ("mutants.jsonl", "manifest.json"):
        assert (tmp_path / "mutants" / name).read_bytes() == (built / "mutants" / name).read_bytes()


def test_outputs_are_never_overwritten(built):
    with pytest.raises(corpus.CorpusError, match="refusing to overwrite"):
        corpus.build_pool(built / "substrates", built / "pool")
    with pytest.raises(corpus.CorpusError, match="refusing to overwrite"):
        corpus.select(
            built / "pool", built / "substrates", built / "mutants", require_compile=False
        )


def test_select_requires_compile_unless_previewing(built, tmp_path):
    with pytest.raises(corpus.CorpusError, match="compile.jsonl"):
        corpus.select(built / "pool", built / "substrates", tmp_path / "out")


def test_tampered_pool_is_rejected(tmp_path):
    substrates = make_substrates(tmp_path / "substrates", ["relu_where"])
    corpus.build_pool(substrates, tmp_path / "pool")
    pool_file = tmp_path / "pool" / "pool.jsonl"
    pool_file.write_text(pool_file.read_text().replace("relu-where-remove", "relu-where-removed"))
    with pytest.raises(corpus.CorpusError, match="does not match"):
        corpus.select(tmp_path / "pool", substrates, tmp_path / "out", require_compile=False)


def test_compile_results_filter_the_pool(tmp_path):
    substrates = make_substrates(tmp_path / "substrates", ["relu_where"])
    pool = tmp_path / "pool"
    corpus.build_pool(substrates, pool)
    rows = [json.loads(x) for x in (pool / "pool.jsonl").read_text().splitlines()]
    kernels = pool / "kernels" / "toy-relu-where"
    parent_hashes = {"relu_kernel": ["parent"]}
    compile_rows = [
        {"substrate_id": "toy-relu-where", "candidate": "parent", "hashes": parent_hashes}
    ]
    device_only = [r for r in rows if r["scope"] == "device"]
    expected = {"compile-fail": 0, "equivalent-to-parent": 0, "duplicate": 0, "distinct": 0}
    for index, row in enumerate(device_only):
        if index == 0:
            compile_rows.append(
                {
                    "substrate_id": "toy-relu-where",
                    "candidate": row["mutant_id"],
                    "error": "CompilationError",
                }
            )
            expected["compile-fail"] += 1
        elif index == 1:
            compile_rows.append(
                {
                    "substrate_id": "toy-relu-where",
                    "candidate": row["mutant_id"],
                    "hashes": parent_hashes,
                }
            )
            expected["equivalent-to-parent"] += 1
        else:
            bucket = "shared" if index in (2, 3) else row["mutant_id"]
            compile_rows.append(
                {
                    "substrate_id": "toy-relu-where",
                    "candidate": row["mutant_id"],
                    "hashes": {"relu_kernel": [bucket]},
                }
            )
            expected["duplicate" if index == 3 else "distinct"] += 1
    for row in rows:
        if row["scope"] == "launch":
            compile_rows.append(
                {
                    "substrate_id": "toy-relu-where",
                    "candidate": row["mutant_id"],
                    "hashes": parent_hashes,
                }
            )
            expected["distinct"] += 1  # same cubins, different launch code
    (pool / "compile.jsonl").write_text("".join(json.dumps(r) + "\n" for r in compile_rows))
    manifest = corpus.select(pool, substrates, tmp_path / "mutants")
    summary = manifest["substrates"][0]
    assert manifest["compile_checked"] is True
    parent_text = (kernels / "parent.py").read_text()
    assert summary["compile"]["parent_compiled_key"] == compiled_key(
        parent_hashes, launch_scope_hash(parent_text)
    )
    assert {k: summary["compile"].get(k, 0) for k in expected} == expected
    assert summary["eligible"] == expected["distinct"]


def test_hack_controls_for_relu_and_softmax(tmp_path):
    substrates = make_substrates(tmp_path / "substrates", ["relu_where", "softmax_rows"])
    kernelbench = make_kernelbench(tmp_path / "kb")
    manifest = corpus.build_controls(substrates, kernelbench, tmp_path / "controls")
    kinds_by_problem: dict[str, set[str]] = {}
    for entry in manifest["controls"]:
        kinds_by_problem.setdefault(entry["problem_id"], set()).add(entry["kind"])
        control = load_kernel_dir(tmp_path / "controls" / entry["control_id"])
        assert control.kind == "control"
        text = control.kernel_path.read_text()
        tree = ast.parse(text)
        classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
        assert classes.count("ModelNew") == 1 and "_Q1SubstrateModelNew" in classes
        assert "_Q1_REFERENCE_SOURCE" in text
    assert kinds_by_problem["L1/19_ReLU"] == {k.name for k in HACK_KINDS}
    assert kinds_by_problem["L1/23_Softmax"] == {
        k.name for k in HACK_KINDS if k.applies_to == "any"
    }


def test_hack_control_renames_every_model_new_reference():
    text, control = build_hack_control(
        next(k for k in HACK_KINDS if k.name == "kbv-h1-identity-shortcut"),
        substrate=substrate_record("toy-relu-inductor", "L1/19_ReLU"),
        substrate_kernel=toy_text("relu_inductor"),
        problem_source=RELU_PROBLEM,
    )
    assert "super(_Q1SubstrateModelNew, self)" in text
    assert "_Q1_NATIVE_SHAPE = (4096, 393216)" in text
    assert control["expected"]["c1"] == "reject"
    assert control["control_kind"] == "hack-emulating-mutant"


def test_mutant_controls_are_emitted_for_hack_emulating_mutants(built):
    manifest = json.loads((built / "mutant-controls" / "controls_manifest.json").read_text())
    assert any(".relu-where-remove." in cid for cid in manifest["controls"])
    for cid in manifest["controls"]:
        control = load_kernel_dir(built / "mutant-controls" / cid)
        assert control.control["expected"]["a"] == "accept"


def test_kernelbench_revision_mismatch_is_refused(tmp_path, monkeypatch):
    substrates = make_substrates(tmp_path / "substrates", ["relu_where"])
    kernelbench = make_kernelbench(tmp_path / "kb")
    monkeypatch.setattr(corpus, "_git_head", lambda path: "f" * 40)
    with pytest.raises(corpus.CorpusError, match="expected"):
        corpus.build_controls(substrates, kernelbench, tmp_path / "controls")


def test_cli_end_to_end_and_exit_codes(tmp_path, capsys):
    substrates = make_substrates(tmp_path / "substrates", ["relu_inductor"])
    assert (
        cli.main(
            ["pool", "--substrates-root", str(substrates), "--pool-root", str(tmp_path / "pool")]
        )
        == 0
    )
    assert (
        cli.main(
            [
                "select",
                "--pool-root",
                str(tmp_path / "pool"),
                "--substrates-root",
                str(substrates),
                "--out-root",
                str(tmp_path / "m"),
                "--no-require-compile",
            ]
        )
        == 0
    )
    assert (
        cli.main(
            ["pool", "--substrates-root", str(substrates), "--pool-root", str(tmp_path / "pool")]
        )
        == 2
    )
    assert cli.main(["table", "rules"]) == 0
    assert cli.main(["table", "operators"]) == 0
    out = capsys.readouterr().out
    assert "relu-max-zero-first-remove" in out


def test_alternate_cap_seeds_keep_the_frozen_split(built, tmp_path):
    corpus.select(
        built / "pool", built / "substrates", tmp_path / "m43", seed=43, require_compile=False
    )
    load = lambda root: {  # noqa: E731
        r["mutant_id"]: r
        for r in map(json.loads, (root / "mutants.jsonl").read_text().splitlines())
    }
    primary, alternate = load(built / "mutants"), load(tmp_path / "m43")
    shared = set(primary) & set(alternate)
    assert shared and set(primary) != set(alternate)
    assert all(primary[m]["split"] == alternate[m]["split"] for m in shared)
    mutation = json.loads((tmp_path / "m43" / sorted(alternate)[0] / "mutation.json").read_text())
    assert mutation["seed"] == 43
