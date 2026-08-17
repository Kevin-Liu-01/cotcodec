from __future__ import annotations

from scripts.probe_graphiti_lifecycle_container import EXPECTED, classify_probe


def _inspect() -> dict:
    return {
        "Id": "sha256:" + "a" * 64,
        "Architecture": "arm64",
        "Config": {
            "Labels": {
                "org.opencontainers.image.revision": EXPECTED["graphiti_revision"],
                "org.cotcodec.source-archive-sha256": EXPECTED[
                    "source_archive_sha256"
                ],
                "org.cotcodec.memory-lifecycle-adapter": EXPECTED["adapter"],
                "org.cotcodec.graphiti-lifecycle-doctor-sha256": EXPECTED[
                    "runner_sha256"
                ],
                "org.cotcodec.graphiti-lifecycle-experiment-sha256": EXPECTED[
                    "experiment_sha256"
                ],
                "org.cotcodec.scientific-result": "false",
            }
        },
    }


def _runs() -> list[dict]:
    return [
        {
            "exit_code": 1,
            "stderr": "The redis-server process failed to start",
            "create_argv": ["docker", "create", "--network", "none"],
            "container_receipt": {
                "container_id": "1" * 64,
                "created_at": "2026-08-15T01:00:00Z",
                "state": {
                    "exit_code": 1,
                    "started_at": "2026-08-15T01:00:01Z",
                    "status": "exited",
                },
            },
        },
        {
            "exit_code": 1,
            "stderr": "The redis-server process failed to start",
            "create_argv": ["docker", "create", "--network", "none"],
            "container_receipt": {
                "container_id": "2" * 64,
                "created_at": "2026-08-15T01:01:00Z",
                "state": {
                    "exit_code": 1,
                    "started_at": "2026-08-15T01:01:01Z",
                    "status": "exited",
                },
            },
        },
    ]


def test_exact_architecture_mismatch_is_classified() -> None:
    checks = classify_probe(
        _inspect(),
        {"redis-server": {"e_machine": 183}, "falkordb.so": {"e_machine": 62}},
        _runs(),
    )
    assert all(checks.values())


def test_matching_module_architecture_does_not_false_report_blocker() -> None:
    checks = classify_probe(
        _inspect(),
        {"redis-server": {"e_machine": 183}, "falkordb.so": {"e_machine": 183}},
        _runs(),
    )
    assert checks["falkordb_module_is_x86_64"] is False


def test_index_only_copy_does_not_count_as_independent_execution() -> None:
    runs = _runs()
    runs[1]["container_receipt"] = dict(runs[0]["container_receipt"])
    checks = classify_probe(
        _inspect(),
        {"redis-server": {"e_machine": 183}, "falkordb.so": {"e_machine": 62}},
        runs,
    )
    assert checks["distinct_container_receipts"] is False
