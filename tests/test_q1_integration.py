"""Q1 integration: substrates -> mutants -> controls -> analysis, and the preregistration.

Pure Python (no torch, no Triton): builds real S1 substrates from the
committed Inductor codegen records and real S2 substrates from the vendored
upstream files, runs the mutator's pool, selection and control steps on them,
and checks that every artifact one component writes is what the next one
reads. The torch end-to-end run through the gates and the audit is
``tests/test_q1_integration_cpu.py``.

It also pins the cross-component agreements the preregistration relies on:
one shared schema file, one exclusion list, the substrate corpus's S1 split and
the mutator's dev/test split as the analysis's splits, and the version card
named in the draft preregistration.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from harness.q1 import analysis, problems, schema, versions
from harness.q1.mutate import corpus
from harness.q1.mutate.sampling import split_of
from harness.q1.substrates import inductor_convert, s2_catalog, sources, split

ROOT = Path(__file__).resolve().parents[1]
RECORDS = Path(__file__).parent / "fixtures" / "q1_substrates"
PREREG = ROOT / "program" / "preregistrations" / "q1-stage0-gate-validation.md"
SCHEMA_SHA256 = "c9bae9d502f7b9c83332f95e24fd9934d91bfe6cede47de527f6d584838b3256"
#: A diverse S2 subset: block pointers, a masked row kernel, a GEMM, Liger, a scan.
S2_KEYS = ("flaggems-relu", "tutorial-fused-softmax", "flaggems-mm", "liger-rms-norm")
KINDS = ("substrate", "mutant", "control")


def _build_substrates(root: Path) -> list[schema.KernelDir]:
    root.mkdir(parents=True)
    for record_path in sorted(RECORDS.glob("L*__*.json")):
        converted = inductor_convert.convert_record(json.loads(record_path.read_text()))
        directory = root / converted.substrate_id
        directory.mkdir()
        for name, text in converted.files().items():
            (directory / name).write_text(text, encoding="utf-8")
        (directory / "substrate.json").write_text(json.dumps(converted.substrate_json))
    rows = s2_catalog.build_all(
        sources.VENDORED_SOURCES_ROOT, problems.PROBLEMS_ROOT, root, only=list(S2_KEYS)
    )
    assert rows and all(row["status"] == "built" for row in rows), rows
    return schema.iter_kernel_dirs(root)


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory: pytest.TempPathFactory) -> dict:
    base = tmp_path_factory.mktemp("q1-integration")
    substrates = _build_substrates(base / "substrates")
    pool = corpus.build_pool(base / "substrates", base / "pool")
    selected = corpus.select(
        base / "pool",
        base / "substrates",
        base / "mutants",
        require_compile=False,
        controls_root=base / "controls-mutants",
    )
    hacks = corpus.build_controls(base / "substrates", None, base / "controls-hacks")
    return {
        "base": base,
        "substrates": substrates,
        "pool": pool,
        "selected": selected,
        "hacks": hacks,
        "roots": [
            base / "substrates",
            base / "mutants",
            base / "controls-mutants",
            base / "controls-hacks",
        ],
    }


def test_shared_schema_is_the_pinned_file() -> None:
    assert schema.sha256_file(ROOT / "harness" / "q1" / "schema.py") == SCHEMA_SHA256
    assert versions.version_card()["schema_py_sha256"] == SCHEMA_SHA256


def test_one_exclusion_list_for_every_component() -> None:
    assert sources.EXCLUDED_PROBLEMS is problems.EXCLUDED_PROBLEMS
    manifest = json.loads((ROOT / "harness/q1/data/shape_manifest.json").read_text())
    assert set(manifest["excluded_problems"]) == set(problems.EXCLUDED_PROBLEMS)
    kept = problems.list_problem_ids()
    assert len(kept) == 196 and not set(kept) & set(problems.EXCLUDED_PROBLEMS)
    assert set(manifest["problems"]) == set(kept)


def test_substrates_use_the_vendored_hash_checked_problems(pipeline: dict) -> None:
    hashes = problems.problem_hashes()
    for kernel in pipeline["substrates"]:
        assert kernel.kind == "substrate"
        assert kernel.problem_id in hashes
        problems.load_problem_source(kernel.problem_id)  # raises on a hash mismatch
        build = json.loads((kernel.path / "build.json").read_text())
        assert build["problem_sha256"] == hashes[kernel.problem_id], kernel.kernel_id


def test_mutants_and_controls_load_under_the_shared_schema(pipeline: dict) -> None:
    table = analysis.kernel_table(pipeline["roots"])
    kinds = {kind: [k for k, v in table.items() if v["kind"] == kind] for kind in KINDS}
    s1 = [k for k in kinds["substrate"] if table[k]["source_kind"] == "inductor"]
    s2_keys = {entry.key for entry in s2_catalog.CATALOG if entry.substrate_id in table}
    assert len(s1) == len(list(RECORDS.glob("L*__*.json"))) == 5
    assert s2_keys == set(S2_KEYS)
    assert pipeline["selected"]["totals"]["selected"] == len(kinds["mutant"]) > 0
    substrate_ids = set(kinds["substrate"])
    for mutant_id in kinds["mutant"]:
        kernel = schema.load_kernel_dir(pipeline["base"] / "mutants" / mutant_id)
        assert kernel.mutation["parent_substrate_id"] in substrate_ids
        parent = pipeline["base"] / "substrates" / kernel.mutation["parent_substrate_id"]
        assert (kernel.path / "substrate.json").read_bytes() == (
            parent / "substrate.json"
        ).read_bytes()
        _, line, col = kernel.mutation["site"].split(":")
        lines = kernel.kernel_path.read_text().splitlines()
        assert 1 <= int(line) <= len(lines) and int(col) <= len(lines[int(line) - 1])
        assert kernel.kernel_path.read_text() != (parent / "kernel.py").read_text()
    # A hack-emulating mutant control exists for the S1 ReLU removal (KBV H.1 analogue).
    mutant_controls = [k for k in kinds["control"] if k.endswith(".control")]
    assert any(".relu-" in k for k in mutant_controls), mutant_controls
    # Every substrate gets the four "any" wrappers; L1/19 gets all eleven kinds.
    hack_ids = {row["control_id"] for row in pipeline["hacks"]["controls"]}
    assert pipeline["hacks"]["kernelbench_source"] == "vendored-hash-checked"
    for substrate_id in substrate_ids:
        assert f"{substrate_id}.hack.decoy-defined-unused" in hack_ids
    relu = [k for k in hack_ids if k.startswith("s1-inductor-L1-19_ReLU.hack.")]
    assert len(relu) == 11, relu


def test_every_control_expectation_names_a_composable_gate(pipeline: dict) -> None:
    table = analysis.kernel_table(pipeline["roots"])
    placeholder = {
        "gates": {},
        "ladder": {},
        "audit": {policy: {} for policy in analysis.POLICIES},
        "A4": "error",
        "tiers": {
            policy: {tier: "error" for tier in ("N", "G", "G-strict", "c-disjoint")}
            for policy in analysis.POLICIES
        },
    }
    controls = [v for v in table.values() if v["kind"] == "control"]
    assert controls
    for facts in controls:
        assert facts["expected"]
        for gate in facts["expected"]:
            assert gate in schema.KNOWN_GATES, gate
            assert analysis.composed_verdict(placeholder, gate) != "unknown-gate", gate


def test_analysis_uses_the_component_splits(pipeline: dict) -> None:
    table = analysis.kernel_table(pipeline["roots"])
    dev, test = analysis.mutant_split(table)
    rows = [
        json.loads(line)
        for line in (pipeline["base"] / "mutants" / "mutants.jsonl").read_text().splitlines()
    ]
    assert {r["mutant_id"] for r in rows if r["split"] == "dev"} == set(dev)
    assert {r["mutant_id"] for r in rows if r["split"] == "test"} == set(test)
    for row in rows:
        assert split_of(row["parent_substrate_id"], row["dedup_hash"]) == row["split"]
    frozen = analysis.s1_split()
    assert frozen == split.calibration_split(problems.list_problem_ids(include_excluded=True))
    assert analysis.calibration_split() == (frozen["calibration"], frozen["evaluation"])
    assert frozen["excluded_before_split"] == sorted(problems.EXCLUDED_PROBLEMS)


def test_corpus_manifests_carry_the_frozen_mutator_identity(pipeline: dict) -> None:
    card = versions.version_card()
    for manifest in (pipeline["pool"], pipeline["selected"], pipeline["hacks"]):
        assert manifest["mutator"]["package_sha256"] == card["mutator_package_sha256"]
        assert manifest["mutator"]["registry_fingerprint"] == card["mutator_registry_fingerprint"]
        assert manifest["mutator"]["schema_version"] == schema.SCHEMA_VERSION
    assert pipeline["selected"]["split_seed"] == 42
    assert card["mutant_split"] == f"{pipeline['selected']['split_version']}/seed=42"


# --- preregistration -------------------------------------------------------------


def _prereg_table(text: str) -> dict[str, str]:
    section = text.split("### 2.1 Frozen component versions", 1)[1].split("\n### 2.2", 1)[0]
    pairs = re.findall(r"^\| `([a-z0-9_]+)` \| `(.+)` \|$", section, flags=re.M)
    return dict(pairs)


def test_preregistration_names_the_versions_it_will_freeze() -> None:
    text = PREREG.read_text(encoding="utf-8")
    named = _prereg_table(text)
    card = versions.version_card()
    expected = {
        key: json.dumps(value) if isinstance(value, list | int) else str(value)
        for key, value in card.items()
    }
    stale = {k: (named.get(k), v) for k, v in expected.items() if named.get(k) != v}
    assert not stale, (
        "the draft preregistration's version table is stale; regenerate it with "
        f"`python scripts/q1_version_card.py --markdown`: {stale}"
    )


def test_preregistration_is_one_freezable_draft() -> None:
    text = PREREG.read_text(encoding="utf-8")
    assert not re.search(r"\bTBD\b|<[A-Za-z_ -]+>", text)  # scripts/preregister.py's rule
    # The component drafts were merged into this one; only one id gets frozen.
    for retired in ("q1-stage0-mutant-corpus.md", "q1-stage0-substrate-corpus.md"):
        assert not (PREREG.parent / retired).exists(), retired
    card = versions.version_card()
    for needle in (
        "q1-stage0-gate-validation",
        card["s1_split_sha256"],
        card["mutator_registry_fingerprint"],
        "q1-mutant-split/v1/seed=42",
        'Random(f"{seed}:L{level}")',
        "Seeds 42, 43 and 44",
    ):
        assert needle in text, needle
    # Every gate id the draft's control table or metrics use is a schema gate id.
    for gate in re.findall(r"`(audit_(?:[A-Z][A-Za-z_]*|c_disjoint))`", text):
        assert gate in schema.KNOWN_GATES, gate


# --- job manifests ---------------------------------------------------------------

Q1_MANIFESTS = (
    "experiments/manifests/q1-substrate-admission.yaml",
    "experiments/manifests/q1-mutate/specializations-v1.yaml",
    "experiments/manifests/q1-core/q1-gate-gpu-smoke.yaml",
    "experiments/manifests/q1-core/q1-stage0-trim-job.template.yaml",
    "experiments/manifests/q1-core/q1-audit-hole-replay.yaml",
    "experiments/manifests/q1-core/q1-pilot-smoke.template.yaml",
    "experiments/manifests/q1-core/q1-pilot-cost.template.yaml",
    "experiments/manifests/q1-core/q1-pilot-concurrency.template.yaml",
)


def _fill(value, key: str = ""):
    if isinstance(value, dict):
        return {k: _fill(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill(v, key) for v in value]
    if value == "FILL-study-artifact-sha256":
        return "d" * 64
    if value == "FILL-study-artifact-size":
        return 1024
    if isinstance(value, str) and value.startswith("FILL-"):
        if key in {"git_sha", "revision"}:
            return "a" * 40
        if key == "host_path":
            return "/home/kevin/cotcodec-runs/stage0/q1-gates/pilot/" + value.removeprefix("FILL-")
        if key == "image_id":
            return "sha256:" + "c" * 64
        if key == "git_sha":
            return "a" * 40
        if key == "source_sha256":
            return "b" * 64
        return "/workspace/cotcodec/" + value.removeprefix("FILL-")
    return value


@pytest.mark.parametrize("relative", Q1_MANIFESTS)
def test_q1_manifests_fail_closed_until_filled(relative: str) -> None:
    yaml = pytest.importorskip("yaml")
    from scripts import submit_docker_research_job as submitter

    raw = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
    with pytest.raises(ValueError):
        submitter.validate_manifest(dict(raw), verify_claim_files=False)
    manifest = submitter.validate_manifest(_fill(raw), verify_claim_files=False)
    assert manifest["model"]["kind"] == "none"
    assert manifest["gpus"] == 1
    command = manifest["command"]
    # Triton JIT needs an exec cache directory: either the profile mounts /tmp
    # with exec, or the cache is redirected to /outputs.
    exec_tmp = manifest.get("container_profile") in {"vllm", "large-cpu-mem"}
    assert exec_tmp or "TRITON_CACHE_DIR=/outputs/cache/triton" in command, relative


def test_core_controls_cover_the_evaluation_problems(tmp_path: Path) -> None:
    from harness.q1 import controls

    written = controls.write_controls(tmp_path / "controls-core")
    loaded = {k.kernel_id: k for k in schema.iter_kernel_dirs(tmp_path / "controls-core")}
    assert set(written) == set(loaded)
    evaluation = set(analysis.s1_split()["evaluation"])
    s2_problems = {entry.problem_id for entry in s2_catalog.CATALOG}
    identity = {
        k.problem_id for k in loaded.values() if k.control["control_kind"] == "reference-identity"
    }
    assert identity == evaluation | s2_problems
    vendored = json.loads((ROOT / "harness/q1/third_party/kernelbench/SOURCES.json").read_text())
    pinned = {Path(f["local"]).name: f["sha256"] for f in vendored["files"]}
    adversarial = [
        k for k in loaded.values() if k.control["control_kind"] == "kernelbench-adversarial"
    ]
    assert len(adversarial) == 3
    for kernel in adversarial:
        name = Path(kernel.control["origin_path"]).name
        assert schema.sha256_file(kernel.kernel_path) == pinned[name]
        assert kernel.problem_id == "L1/1_Square_matrix_multiplication_"
    sample = loaded[controls.identity_control_id("L1/19_ReLU")]
    assert sample.kernel_path.read_text().endswith("\n\nModelNew = Model\n")
    with pytest.raises(FileExistsError):
        controls.write_controls(tmp_path / "controls-core")
