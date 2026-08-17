#!/usr/bin/env python3
"""Seal the exact Fidelis zero-LLM LongMemEval-S retrieval reproduction."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Any

FIDELIS_REPOSITORY = "https://github.com/hermes-labs-ai/fidelis"
FIDELIS_REVISION = "0950ff3e6d377b08f02a26045a6508c58a07a1eb"
FIDELIS_TREE = "d50069ac435f801e392c6565f6f9598a415b7e09"
FIDELIS_SOURCE_ARCHIVE_SHA256 = (
    "54ef4551964e2f62ff2b8fffcd82d2fffa309b8b3d025b68dfcaa7111dd8b91b"
)
PIPELINE_SHA256 = "6cdafd387e394a4fbbe9bda7c77098f2f571cc16dc91e104acffa7aa44882a66"
LICENSE_SHA256 = "32272de4bccdba865f5b21f9b83107634c0a90455008db8acb8e62b9ced15598"
PYPROJECT_SHA256 = "2f3a8ae416d577edf8fa4e8349b8409332372d6d99a2669f70c6fd48d07963b8"
DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
DATASET_REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
DATASET_SIZE = 277383467
DATASET_URL = (
    "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/"
    f"{DATASET_REVISION}/longmemeval_s_cleaned.json?download=true"
)
SHARD_MANIFEST_SHA256 = (
    "a11f114df974e4553c6f65215b0098c3b90607932d2aeeaa4a56b65c867a7e48"
)
QUESTION_ID_ROOT_SHA256 = (
    "64f3cd4468dba3580b6eaadf735de55efbdec955e627f5e3fbf5b9d392d15efe"
)
PROJECTION_SHA256 = "47d1457cdc1b6e5c0439cca87933b4bb3e3eb220aa82eeb456f51869514c746d"
UPSTREAM_PER_QUESTION_SHA256 = (
    "aa93767be273060d39d31f4bd22b938a50b27304b4543194c95f3ef1232f2912"
)
UPSTREAM_AGGREGATE_SHA256 = (
    "217997e2b60c9035d49d0821e149658da99ba6508ef57039640e32190b989ac6"
)
OLLAMA_ARCHIVE_SHA256 = (
    "6ea25ae105a3e807aab1fedad84126f6ffaea4b5eb5d198c98f24bea1d0dd1ba"
)
OLLAMA_BINARY_SHA256 = (
    "db51a3fb2613fff17235c5123ec5d3f07193068997230c61e1b66cf98a86ca93"
)
OLLAMA_DRIFT_ARCHIVE_SHA256 = (
    "17a5b096d4515d00a6415012db847a2b353b389ed7ab33d025e3b98c2f05b49c"
)
OLLAMA_DRIFT_BINARY_SHA256 = (
    "ee63fd25df47b95b5ff762d28b40734699b6d61f88de6348946c9dd507c103d9"
)
OLLAMA_DRIFT_RUN_SHA256 = (
    "f8db09b3761026ddec0b17f24326c3c2c8b782c6f5182062c839cf3dea0e0ee1"
)
MODEL_MANIFEST_SHA256 = (
    "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f"
)
MODEL_BLOBS = {
    "sha256:31df23ea7daa448f9ccdbbcecce6c14689c8552222b80defd3830707c0139d4f": 420,
    "sha256:970aa74c0a90ef7482477cf803618e776e173c007bf957f635f1015bfcfef0e6": 274290656,
    "sha256:c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4": 11357,
    "sha256:ce4a164fc04605703b485251fe9f1a181688ba0eb6badb80cc6335c0de17ca0d": 17,
}
EXPECTED_PACKAGES = {"bm25s": "0.3.3", "numpy": "2.4.4"}
EXPECTED_PACKAGE_TREES = {
    "bm25s": {
        "file_count": 21,
        "root_sha256": "6a2c59ca38238a334cd59ebda40945867aeb23eca60e1e8137c2176d21771f97",
    },
    "numpy": {
        "file_count": 1017,
        "root_sha256": "e5f82691a0892919741c723e7e3ef29cd82760cecd4644d3733fcd5845869207",
    },
}
PYTHON_EXECUTABLE_SHA256 = (
    "b8014caecb1f334bbc67e99b74d9f5fa6e3519c6567c98a890940b31ffeffa32"
)
PYTHON_VENV_CONFIG_SHA256 = (
    "27cc03722145ad7ca42200bf064bff051557f628b0ee9a19132b3a9d6b109ce7"
)
EXPECTED_DEPENDENCY_WHEELS = {
    "bm25s-0.3.3-py3-none-any.whl": (
        "03941f4e2a3610cbbaefa614c22d0e164a53c1e3201a4330cba45081260fd934"
    ),
    "numpy-2.4.4-cp311-cp311-macosx_14_0_arm64.whl": (
        "86b6f55f5a352b48d7fbfd2dbc3d5b780b2d79f4d3c121f33eb6efb22e9a2015"
    ),
}
EXPECTED_HOST = {
    "system": "Darwin",
    "kernel_release": "25.4.0",
    "machine": "arm64",
    "macos_version": "26.4",
    "macos_build": "25E246",
    "cpu": "Apple M5 Max",
}
def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular(path: Path, label: str, *, resolve_symlink: bool = False) -> Path:
    candidate = path.resolve() if resolve_symlink else path
    if not candidate.is_file() or (not resolve_symlink and candidate.is_symlink()):
        raise ValueError(f"{label} must be a regular non-symlink file")
    return candidate


def _load_json(path: Path, label: str) -> Any:
    _regular(path, label)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid JSON") from exc


def _git(checkout: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise ValueError(
            f"git {' '.join(arguments)} failed: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    return completed.stdout.strip()


def _normalize_repository(value: str) -> str:
    normalized = value.strip().removesuffix("/").removesuffix(".git")
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized.removeprefix("git@github.com:")
    return normalized


def _verify_source(checkout: Path) -> dict[str, str]:
    if not checkout.is_dir() or checkout.is_symlink():
        raise ValueError("Fidelis checkout must be a regular directory")
    expected = {
        "revision": FIDELIS_REVISION,
        "tree": FIDELIS_TREE,
        "repository": FIDELIS_REPOSITORY,
    }
    actual = {
        "revision": _git(checkout, "rev-parse", "HEAD"),
        "tree": _git(checkout, "rev-parse", "HEAD^{tree}"),
        "repository": _normalize_repository(_git(checkout, "remote", "get-url", "origin")),
    }
    if actual != expected:
        raise ValueError("Fidelis checkout identity drifted")
    if _git(checkout, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Fidelis checkout must be completely clean")
    archive = subprocess.run(
        ["git", "-C", str(checkout), "archive", "--format=tar", "HEAD"],
        check=False,
        capture_output=True,
    )
    if (
        archive.returncode
        or _sha256_bytes(archive.stdout) != FIDELIS_SOURCE_ARCHIVE_SHA256
    ):
        raise ValueError("Fidelis source archive bytes drifted")
    pipeline = checkout / "bench/longmemeval_combined_pipeline_v35.py"
    if _sha256_file(_regular(pipeline, "Fidelis pipeline")) != PIPELINE_SHA256:
        raise ValueError("Fidelis pipeline bytes drifted")
    if _sha256_file(_regular(checkout / "LICENSE", "Fidelis license")) != LICENSE_SHA256:
        raise ValueError("Fidelis license bytes drifted")
    if _sha256_file(_regular(checkout / "pyproject.toml", "Fidelis pyproject")) != (
        PYPROJECT_SHA256
    ):
        raise ValueError("Fidelis pyproject bytes drifted")
    return actual


def _verify_model(manifest_path: Path, model_dir: Path) -> dict[str, Any]:
    manifest = _load_json(manifest_path, "Ollama model manifest")
    if _sha256_file(manifest_path) != MODEL_MANIFEST_SHA256:
        raise ValueError("Ollama model manifest drifted")
    descriptors = [manifest.get("config"), *manifest.get("layers", [])]
    observed: dict[str, int] = {}
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise ValueError("Ollama model descriptor is invalid")
        digest = descriptor.get("digest")
        size = descriptor.get("size")
        if digest not in MODEL_BLOBS or size != MODEL_BLOBS[digest]:
            raise ValueError("Ollama model descriptor drifted")
        blob = model_dir / "blobs" / digest.replace(":", "-")
        if _sha256_file(_regular(blob, f"model blob {digest}")) != digest.removeprefix(
            "sha256:"
        ):
            raise ValueError("Ollama model blob digest drifted")
        if blob.stat().st_size != size:
            raise ValueError("Ollama model blob size drifted")
        observed[digest] = size
    if observed != MODEL_BLOBS:
        raise ValueError("Ollama model blob roster drifted")
    return {
        "name": "nomic-embed-text:latest",
        "manifest_sha256": MODEL_MANIFEST_SHA256,
        "blobs": observed,
    }


def _package_tree(path: Path, label: str) -> dict[str, Any]:
    if not path.is_dir() or path.is_symlink():
        raise ValueError(f"{label} package root must be a regular directory")
    candidates = list(path.rglob("*"))
    if any(candidate.is_symlink() for candidate in candidates):
        raise ValueError(f"{label} package tree cannot contain symbolic links")
    files = sorted(
        candidate
        for candidate in candidates
        if candidate.is_file()
        and "__pycache__" not in candidate.parts
        and candidate.suffix != ".pyc"
    )
    digest = hashlib.sha256()
    for candidate in files:
        relative = candidate.relative_to(path).as_posix()
        digest.update(f"{relative}\t{_sha256_file(candidate)}\n".encode())
    return {"file_count": len(files), "root_sha256": digest.hexdigest()}


def _runtime_versions(python_path: Path) -> dict[str, Any]:
    launcher = Path(os.path.abspath(os.fspath(python_path)))
    if not launcher.is_file() or not launcher.is_symlink():
        raise ValueError("Fidelis Python launcher must be a virtual-environment symlink")
    executable = _regular(launcher, "Python executable", resolve_symlink=True)
    executable_sha256 = _sha256_file(executable)
    if executable_sha256 != PYTHON_EXECUTABLE_SHA256:
        raise ValueError("Fidelis Python executable bytes drifted")
    venv_config = launcher.parent.parent / "pyvenv.cfg"
    if _sha256_file(_regular(venv_config, "Python virtual-environment config")) != (
        PYTHON_VENV_CONFIG_SHA256
    ):
        raise ValueError("Fidelis Python virtual-environment config drifted")
    code = (
        "import json,pathlib,platform,bm25s,numpy;"
        "print(json.dumps({'python':platform.python_version(),"
        "'bm25s':bm25s.__version__,'numpy':numpy.__version__,"
        "'module_roots':{'bm25s':str(pathlib.Path(bm25s.__file__).resolve().parent),"
        "'numpy':str(pathlib.Path(numpy.__file__).resolve().parent)}},sort_keys=True))"
    )
    completed = subprocess.run(
        [str(launcher), "-c", code], check=False, capture_output=True, text=True
    )
    if completed.returncode:
        raise ValueError("pinned Python environment cannot import Fidelis dependencies")
    try:
        versions = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("pinned Python environment emitted invalid version data") from exc
    if {key: versions.get(key) for key in EXPECTED_PACKAGES} != EXPECTED_PACKAGES:
        raise ValueError("Fidelis dependency versions drifted")
    roots = versions.pop("module_roots", None)
    if not isinstance(roots, dict) or set(roots) != set(EXPECTED_PACKAGES):
        raise ValueError("Fidelis dependency module roots drifted")
    package_trees = {
        name: _package_tree(Path(roots[name]), name) for name in sorted(roots)
    }
    if package_trees != EXPECTED_PACKAGE_TREES:
        raise ValueError("Fidelis installed dependency bytes drifted")
    return {
        **versions,
        "executable_sha256": executable_sha256,
        "venv_config_sha256": PYTHON_VENV_CONFIG_SHA256,
        "package_trees": package_trees,
    }


def _verify_dependency_wheels(paths: list[Path]) -> dict[str, str]:
    if len(paths) != len(EXPECTED_DEPENDENCY_WHEELS):
        raise ValueError("Fidelis dependency wheel roster drifted")
    observed: dict[str, str] = {}
    for path in paths:
        wheel = _regular(path, "Fidelis dependency wheel")
        if wheel.name in observed:
            raise ValueError("Fidelis dependency wheel roster contains a duplicate")
        observed[wheel.name] = _sha256_file(wheel)
    if observed != EXPECTED_DEPENDENCY_WHEELS:
        raise ValueError("Fidelis dependency wheel bytes drifted")
    return observed


def _host_receipt() -> dict[str, str]:
    commands = {
        "macos_version": ["sw_vers", "-productVersion"],
        "macos_build": ["sw_vers", "-buildVersion"],
        "cpu": ["sysctl", "-n", "machdep.cpu.brand_string"],
    }
    actual = {
        "system": platform.system(),
        "kernel_release": platform.release(),
        "machine": platform.machine(),
    }
    for key, command in commands.items():
        completed = subprocess.run(
            command, check=False, capture_output=True, text=True
        )
        if completed.returncode:
            raise ValueError(f"cannot resolve Fidelis host field {key}")
        actual[key] = completed.stdout.strip()
    if actual != EXPECTED_HOST:
        raise ValueError("Fidelis host runtime identity drifted")
    return actual


def _verify_shards(
    dataset: list[dict[str, Any]], manifest: dict[str, Any], manifest_path: Path
) -> tuple[list[str], list[list[str]]]:
    rows = [row for row in dataset if "_abs" not in row["question_id"]]
    qids = [row["question_id"] for row in rows]
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != "FIDELIS_LONGMEMEVAL_SHARDS_PREPARED"
        or manifest.get("source_dataset_sha256") != DATASET_SHA256
        or manifest.get("source_row_count") != len(dataset)
        or manifest.get("non_abstention_row_count") != len(rows)
        or manifest.get("question_id_root_sha256") != _sha256_bytes(_canonical(qids))
        or manifest.get("question_id_root_sha256") != QUESTION_ID_ROOT_SHA256
    ):
        raise ValueError("Fidelis shard manifest identity drifted")
    shards = manifest.get("shards")
    if not isinstance(shards, list) or len(shards) != manifest.get("shard_count"):
        raise ValueError("Fidelis shard roster drifted")
    restored: list[str] = []
    shard_question_ids: list[list[str]] = []
    for index, shard in enumerate(shards):
        if not isinstance(shard, dict) or shard.get("index") != index:
            raise ValueError("Fidelis shard record drifted")
        shard_path = manifest_path.parent / shard["relative_path"]
        shard_rows = _load_json(shard_path, f"Fidelis shard {index}")
        shard_qids = [row["question_id"] for row in shard_rows]
        if (
            _sha256_file(shard_path) != shard.get("sha256")
            or len(shard_rows) != shard.get("row_count")
            or shard_qids[0] != shard.get("first_question_id")
            or shard_qids[-1] != shard.get("last_question_id")
        ):
            raise ValueError("Fidelis shard contents drifted")
        restored.extend(shard_qids)
        shard_question_ids.append(shard_qids)
    if restored != qids:
        raise ValueError("Fidelis shards do not restore the exact question roster")
    return qids, shard_question_ids


def _embed_projection(projection: list[dict[str, Any]]) -> dict[str, Any]:
    encoded = _canonical(projection)
    compressed = gzip.compress(encoded, mtime=0)
    return {
        "encoding": "canonical-json+gzip+base64",
        "row_count": len(projection),
        "bytes": len(encoded),
        "sha256": _sha256_bytes(encoded),
        "compressed_bytes": len(compressed),
        "compressed_sha256": _sha256_bytes(compressed),
        "content_gzip_base64": base64.b64encode(compressed).decode(),
    }


def _compare_results(
    *,
    question_ids: list[str],
    dataset_rows: list[dict[str, Any]],
    run_paths: list[Path],
    expected_run_question_ids: list[list[str]] | None = None,
    upstream_path: Path,
    upstream_aggregate: dict[str, Any],
) -> dict[str, Any]:
    upstream_rows = _load_json(upstream_path, "upstream per-question artifact")
    if not isinstance(upstream_rows, list) or not all(
        isinstance(row, dict) for row in upstream_rows
    ):
        raise ValueError("upstream per-question artifact must be a list of mappings")
    upstream = {row["qid"]: row for row in upstream_rows}
    if list(upstream) != question_ids:
        raise ValueError("upstream per-question roster differs from the dataset")
    dataset = {row["question_id"]: row for row in dataset_rows}
    if list(dataset) != question_ids:
        raise ValueError("dataset row projection differs from its question roster")

    local: dict[str, dict[str, Any]] = {}
    run_receipts: list[dict[str, Any]] = []
    for index, path in enumerate(run_paths):
        rows = _load_json(path, f"local run shard {index}")
        if (
            not isinstance(rows, list)
            or not rows
            or not all(isinstance(row, dict) for row in rows)
        ):
            raise ValueError("local run shard must contain a non-empty list of mappings")
        if expected_run_question_ids is not None and [row.get("qid") for row in rows] != (
            expected_run_question_ids[index]
        ):
            raise ValueError(f"local run shard {index} question roster drifted")
        for row in rows:
            qid = row.get("qid")
            if qid in local:
                raise ValueError("local run shards contain a duplicate question")
            local[qid] = row
        run_receipts.append(
            {"index": index, "row_count": len(rows), "sha256": _sha256_file(path)}
        )
    if list(local) != question_ids:
        if set(local) != set(question_ids):
            raise ValueError("local run shards are incomplete or contain foreign questions")
        local = {qid: local[qid] for qid in question_ids}

    projection: list[dict[str, Any]] = []
    r1_hits = 0
    r5_hits = 0
    temporal_boost_questions = 0
    for qid in question_ids:
        observed = local[qid]
        expected = upstream[qid]
        source = dataset[qid]
        gold = set(source["answer_session_ids"])
        expected_top5 = expected.get("s1_top5_ids", [])
        if (
            expected.get("question") != source.get("question")
            or expected.get("qtype") != source.get("question_type")
            or set(expected.get("gold_session_ids", [])) != gold
            or not set(expected_top5).issubset(set(source["haystack_session_ids"]))
            or expected.get("s1_hit_at_1") != bool(gold.intersection(expected_top5[:1]))
            or expected.get("s1_hit_at_5") != bool(gold.intersection(expected_top5[:5]))
        ):
            raise ValueError(f"Fidelis upstream result is inconsistent with the dataset at {qid}")
        if (
            observed.get("question") != expected.get("question")
            or observed.get("qtype") != expected.get("qtype")
            or set(observed.get("gold_session_ids", []))
            != set(expected.get("gold_session_ids", []))
            or observed.get("s1_top5_ids") != expected.get("s1_top5_ids")
            or observed.get("s1_top5_scores") != expected.get("s1_top5_scores")
            or observed.get("s1_hit_at_1") != expected.get("s1_hit_at_1")
            or observed.get("s1_hit_at_5") != expected.get("s1_hit_at_5")
            or observed.get("temporal_boost_fired")
            != expected.get("temporal_boost_fired")
            or observed.get("temporal_boost_count")
            != expected.get("temporal_boost_count")
        ):
            raise ValueError(f"Fidelis local result differs from upstream at {qid}")
        if (
            observed.get("route_decision") != "no_filter"
            or observed.get("filter_called") is not False
            or observed.get("filter_ms") != 0
            or observed.get("s2_top5_ids") != observed.get("s1_top5_ids")
        ):
            raise ValueError(f"Fidelis zero-LLM contract drifted at {qid}")
        r1_hits += int(observed["s1_hit_at_1"])
        r5_hits += int(observed["s1_hit_at_5"])
        temporal_boost_questions += int(observed["temporal_boost_fired"])
        projection.append(
            {
                "qid": qid,
                "top5_ids": observed["s1_top5_ids"],
                "top5_scores": observed["s1_top5_scores"],
                "r1": observed["s1_hit_at_1"],
                "r5": observed["s1_hit_at_5"],
            }
        )

    count = len(question_ids)
    metrics = {
        "question_count": count,
        "recall_any_at_1_hits": r1_hits,
        "recall_any_at_1": r1_hits / count,
        "recall_any_at_5_hits": r5_hits,
        "recall_any_at_5": r5_hits / count,
    }
    claimed = upstream_aggregate.get("stage1b_metrics", {}).get("recall_any", {})
    if (
        upstream_aggregate.get("questions_evaluated") != count
        or round(metrics["recall_any_at_1"], 3) != claimed.get("R@1")
        or round(metrics["recall_any_at_5"], 3) != claimed.get("R@5")
    ):
        raise ValueError("recomputed Fidelis metrics differ from the upstream aggregate")
    return {
        "metrics": metrics,
        "question_id_root_sha256": _sha256_bytes(_canonical(question_ids)),
        "exact_top5_id_match_count": count,
        "exact_logged_score_match_count": count,
        "temporal_boost_question_count": temporal_boost_questions,
        "run_files": run_receipts,
        "projection": _embed_projection(projection),
    }


def _verify_runtime_drift(
    *, drift_run_path: Path, upstream_path: Path
) -> dict[str, Any]:
    if _sha256_file(_regular(drift_run_path, "Ollama drift run")) != OLLAMA_DRIFT_RUN_SHA256:
        raise ValueError("Ollama drift-run artifact drifted")
    drift_rows = _load_json(drift_run_path, "Ollama drift run")
    upstream_rows = _load_json(upstream_path, "upstream per-question artifact")
    if (
        not isinstance(drift_rows, list)
        or len(drift_rows) != 1
        or not isinstance(drift_rows[0], dict)
    ):
        raise ValueError("Ollama drift run must contain exactly one question")
    if not isinstance(upstream_rows, list) or not upstream_rows or not isinstance(
        upstream_rows[0], dict
    ):
        raise ValueError("upstream per-question artifact is invalid")
    observed = drift_rows[0]
    expected = upstream_rows[0]
    if (
        observed.get("qid") != expected.get("qid")
        or observed.get("qid") != "e47becba"
        or observed.get("s1_top5_ids") == expected.get("s1_top5_ids")
        or observed.get("s1_hit_at_1") is not False
        or expected.get("s1_hit_at_1") is not True
        or observed.get("s1_hit_at_5") is not True
    ):
        raise ValueError("Ollama runtime-drift falsifier no longer reproduces")
    return {
        "status": "RUNTIME_VERSION_CHANGES_RETRIEVAL",
        "question_id": observed["qid"],
        "historical_runtime": "0.20.6",
        "drift_runtime": "0.32.9",
        "drift_release_archive_sha256": OLLAMA_DRIFT_ARCHIVE_SHA256,
        "drift_binary_sha256": OLLAMA_DRIFT_BINARY_SHA256,
        "shared_model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "historical_top5_ids": expected["s1_top5_ids"],
        "drift_top5_ids": observed["s1_top5_ids"],
        "historical_recall_any_at_1": True,
        "drift_recall_any_at_1": False,
        "drift_recall_any_at_5": True,
        "drift_run_sha256": OLLAMA_DRIFT_RUN_SHA256,
    }


def _write_once(path: Path, payload: dict[str, Any]) -> None:
    path = Path(os.path.abspath(os.fspath(path)))
    if any(component.is_symlink() for component in (path, *path.parents)):
        raise ValueError("Fidelis evidence output path cannot contain symbolic links")
    if path.exists() or path.is_symlink():
        raise ValueError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True).encode() + b"\n"
    with tempfile.NamedTemporaryFile(
        prefix=f".{path.name}.", dir=path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
        temporary.write(encoded)
        temporary.flush()
        os.fsync(temporary.fileno())
    try:
        os.link(temporary_path, path)
    except FileExistsError as exc:
        raise ValueError(f"refusing to overwrite {path}") from exc
    finally:
        temporary_path.unlink(missing_ok=True)


def seal(args: argparse.Namespace) -> dict[str, Any]:
    if len(args.run_file) != 4 or args.ollama_num_parallel != 4:
        raise ValueError("Fidelis evidence requires four run shards and Ollama parallelism 4")
    source = _verify_source(args.source_checkout)
    for path, expected, label in (
        (args.dataset, DATASET_SHA256, "LongMemEval dataset"),
        (args.upstream_per_question, UPSTREAM_PER_QUESTION_SHA256, "upstream result"),
        (args.upstream_aggregate, UPSTREAM_AGGREGATE_SHA256, "upstream aggregate"),
        (args.ollama_archive, OLLAMA_ARCHIVE_SHA256, "Ollama release archive"),
        (args.ollama_binary, OLLAMA_BINARY_SHA256, "Ollama binary"),
        (
            args.ollama_drift_archive,
            OLLAMA_DRIFT_ARCHIVE_SHA256,
            "Ollama drift release archive",
        ),
        (args.ollama_drift_binary, OLLAMA_DRIFT_BINARY_SHA256, "Ollama drift binary"),
    ):
        if _sha256_file(_regular(path, label)) != expected:
            raise ValueError(f"{label} digest drifted")
    dataset = _load_json(args.dataset, "LongMemEval dataset")
    if (
        not isinstance(dataset, list)
        or len(dataset) != 500
        or not all(
            isinstance(row, dict) and isinstance(row.get("question_id"), str)
            for row in dataset
        )
    ):
        raise ValueError("LongMemEval dataset roster drifted")
    shard_manifest = _load_json(args.shard_manifest, "Fidelis shard manifest")
    if not isinstance(shard_manifest, dict):
        raise ValueError("Fidelis shard manifest must be a mapping")
    if _sha256_file(args.shard_manifest) != SHARD_MANIFEST_SHA256:
        raise ValueError("Fidelis shard manifest bytes drifted")
    question_ids, shard_question_ids = _verify_shards(
        dataset, shard_manifest, args.shard_manifest
    )
    upstream_aggregate = _load_json(args.upstream_aggregate, "upstream aggregate")
    if not isinstance(upstream_aggregate, dict):
        raise ValueError("upstream aggregate must be a mapping")
    result = _compare_results(
        question_ids=question_ids,
        dataset_rows=[
            row for row in dataset if "_abs" not in row["question_id"]
        ],
        run_paths=args.run_file,
        expected_run_question_ids=shard_question_ids,
        upstream_path=args.upstream_per_question,
        upstream_aggregate=upstream_aggregate,
    )
    if result["projection"]["sha256"] != PROJECTION_SHA256:
        raise ValueError("Fidelis exact claim projection drifted")
    bundle = {
        "schema_version": 1,
        "status": "FIDELIS_ZERO_LLM_RETRIEVAL_REPRODUCTION_PASS",
        "source_id": "fidelis",
        "evidence_grade": "local-reproduced",
        "evidence_kind": "zero-llm-retrieval-benchmark-reproduction",
        "scientific_result": True,
        "publication_ready": False,
        "runtime_lane": "local-arm64-bound-artifact-runtime",
        "source_revisions": {FIDELIS_REPOSITORY: FIDELIS_REVISION},
        "source_tree": source["tree"],
        "source_archive_sha256": FIDELIS_SOURCE_ARCHIVE_SHA256,
        "source_license": "MIT",
        "source_file_sha256": {
            "LICENSE": LICENSE_SHA256,
            "pyproject.toml": PYPROJECT_SHA256,
            "bench/longmemeval_combined_pipeline_v35.py": PIPELINE_SHA256,
        },
        "pipeline_sha256": PIPELINE_SHA256,
        "dataset": {
            "name": "LongMemEval-S cleaned",
            "url": DATASET_URL,
            "revision": DATASET_REVISION,
            "license": "MIT",
            "sha256": DATASET_SHA256,
            "size": DATASET_SIZE,
            "source_row_count": len(dataset),
            "non_abstention_row_count": len(question_ids),
        },
        "upstream_artifacts": {
            "per_question_path": "bench/runs/runP-v35/per_question.json",
            "per_question_sha256": UPSTREAM_PER_QUESTION_SHA256,
            "aggregate_path": "bench/runs/runP-v35/aggregate.json",
            "aggregate_sha256": UPSTREAM_AGGREGATE_SHA256,
        },
        "runtime": {
            "host": _host_receipt(),
            "ollama_version": "0.20.6",
            "ollama_release_archive_sha256": OLLAMA_ARCHIVE_SHA256,
            "ollama_binary_sha256": OLLAMA_BINARY_SHA256,
            "ollama_num_parallel": args.ollama_num_parallel,
            "model": _verify_model(args.model_manifest, args.model_dir),
            "python": _runtime_versions(args.python),
            "dependency_wheels": _verify_dependency_wheels(args.dependency_wheel),
        },
        "runtime_drift_falsifier": _verify_runtime_drift(
            drift_run_path=args.drift_run_file,
            upstream_path=args.upstream_per_question,
        ),
        "instrumentation_findings": {
            "temporal_boost_question_count": result["temporal_boost_question_count"],
            "logged_top5_id_phase": "post-temporal-boost",
            "logged_top5_score_phase": "pre-temporal-boost",
            "score_id_alignment_guaranteed_for_temporal_boosted_rows": False,
            "metric_recomputation_uses_hit_flags_and_ids_not_logged_scores": True,
            "local_resume_aggregate_excluded": True,
            "local_resume_aggregate_exclusion_reason": (
                "upstream resume restores per-question rows and selected counters but not "
                "retrieval timing or every metric accumulator"
            ),
        },
        "shard_manifest_sha256": SHARD_MANIFEST_SHA256,
        "execution_protocol": {
            "shard_count": 4,
            "resumed_from_incremental_per_question_files": True,
            "local_aggregate_used": False,
            "upstream_stage2_or_qa_reproduced": False,
            "compared_fields": [
                "question",
                "qtype",
                "gold_session_ids",
                "s1_top5_ids",
                "s1_top5_scores",
                "s1_hit_at_1",
                "s1_hit_at_5",
                "temporal_boost_fired",
                "temporal_boost_count",
            ],
        },
        "result": result,
        "claim_boundary": {
            "retrieval_hot_path_zero_llm": True,
            "write_path_evaluated": False,
            "persistence_lifecycle_evaluated": False,
            "answer_quality_evaluated": False,
            "latency_evaluated": False,
            "packaged_service_equivalence_evaluated": False,
            "out_of_distribution_generalization_evaluated": False,
            "logged_score_id_alignment_fully_valid": False,
            "network_isolation_evaluated": False,
            "external_attestation": False,
            "h100_actor_admission": "cpu-retrieval-gate-pass-common-actor-still-required",
        },
    }
    _write_once(args.output, bundle)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-checkout", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--shard-manifest", type=Path, required=True)
    parser.add_argument("--upstream-per-question", type=Path, required=True)
    parser.add_argument("--upstream-aggregate", type=Path, required=True)
    parser.add_argument("--run-file", type=Path, action="append", required=True)
    parser.add_argument("--ollama-archive", type=Path, required=True)
    parser.add_argument("--ollama-binary", type=Path, required=True)
    parser.add_argument("--ollama-drift-archive", type=Path, required=True)
    parser.add_argument("--ollama-drift-binary", type=Path, required=True)
    parser.add_argument("--drift-run-file", type=Path, required=True)
    parser.add_argument("--model-manifest", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--dependency-wheel", type=Path, action="append", required=True)
    parser.add_argument("--ollama-num-parallel", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        bundle = seal(args)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps({"status": bundle["status"], "result": bundle["result"]["metrics"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
