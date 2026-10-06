#!/usr/bin/env python3
"""Run the pinned Hermes provider contract matrix inside a container.

This is deliberately a CPU conformance runner. It does not start provider
services, accept credentials, or make a memory-quality claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from scripts.validate_hermes_provider_experiment import (
    EXPECTED_IMAGE,
    EXPECTED_ROSTER,
    load_and_validate_experiment,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = (
    PROJECT_ROOT / "experiments" / "memory" / "stage4-hermes-provider-conformance.yaml"
)

HERMES_GROUPS: dict[str, tuple[str, ...]] = {
    "byterover": ("tests/plugins/memory/test_byterover_provider.py",),
    "hindsight": (
        "tests/plugins/memory/test_hindsight_config_schema.py",
        "tests/plugins/memory/test_hindsight_env_perms.py",
        "tests/plugins/memory/test_hindsight_local_runtime_hint.py",
        "tests/plugins/memory/test_hindsight_provider.py",
        "tests/plugins/memory/test_hindsight_templates.py",
        "tests/plugins/test_hindsight_health_grace_timeout.py",
        "tests/plugins/test_hindsight_root_guard.py",
    ),
    "holographic": (
        "tests/plugins/memory/test_holographic_auto_extract.py",
        "tests/plugins/memory/test_holographic_retrieval.py",
        "tests/plugins/memory/test_holographic_shutdown_closes_db.py",
        "tests/plugins/memory/test_holographic_store.py",
        "tests/plugins/test_holographic_vector_storage.py",
    ),
    "honcho": (
        "tests/plugins/memory/test_honcho_cli_peers.py",
        "tests/plugins/memory/test_honcho_config_schema.py",
        "tests/honcho_plugin",
        "tests/test_honcho_client_concurrency.py",
        "tests/test_honcho_client_config.py",
        "tests/test_honcho_session_context.py",
        "tests/test_honcho_startup_fail_open.py",
    ),
    "mem0": (
        "tests/plugins/memory/test_mem0_backend.py",
        "tests/plugins/memory/test_mem0_providers.py",
        "tests/plugins/memory/test_mem0_setup.py",
        "tests/plugins/memory/test_mem0_v3.py",
    ),
    "openviking": (
        "tests/plugins/memory/test_openviking_endpoint_always_blocked.py",
        "tests/plugins/memory/test_openviking_provider.py",
        "tests/plugins/memory/test_openviking_shutdown.py",
        "tests/openviking_plugin",
    ),
    "retaindb": (
        "tests/plugins/memory/test_retaindb_provider.py",
        "tests/plugins/test_retaindb_plugin.py",
    ),
    "supermemory": ("tests/plugins/memory/test_supermemory_provider.py",),
}
COMMON_GROUP = (
    "tests/plugins/memory/test_config_schema.py",
    "tests/plugins/memory/test_discovery_sources.py",
    "tests/plugins/memory/test_memory_lazy_install.py",
)
MEMORI_TEST_DIR = Path("integrations/hermes/tests")
SUMMARY_RE = re.compile(
    r"(?P<count>\d+) (?P<label>passed|failed|skipped|error|errors|xfailed|xpassed)"
)


class ConformanceError(RuntimeError):
    """Raised when the conformance runtime cannot produce trustworthy output."""


def _regular_directory(path: Path, label: str) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or path.is_symlink():
        raise ConformanceError(f"{label} must be a regular non-symlink directory")
    return resolved


def _canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _write_new(path: Path, encoded: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(fd)


def _prepare_output(path: Path) -> Path:
    parent = path.parent.resolve(strict=True)
    if parent.is_symlink():
        raise ConformanceError("output parent cannot be a symlink")
    path.mkdir(mode=0o700, exist_ok=False)
    return path.resolve(strict=True)


def _git_source_receipt(
    root: Path,
    *,
    expected_revision: str,
    expected_tree: str,
    expected_archive_sha256: str | None = None,
) -> dict[str, Any]:
    if shutil.which("git") is None:
        raise ConformanceError("git is required to verify provider source identity")

    def git(*args: str, text: bool = True) -> subprocess.CompletedProcess[Any]:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=text,
        )
        if completed.returncode != 0:
            stderr = (
                completed.stderr
                if text
                else completed.stderr.decode(errors="replace")
            )
            raise ConformanceError(f"git {' '.join(args)} failed: {stderr.strip()}")
        return completed

    revision = git("rev-parse", "HEAD").stdout.strip()
    tree = git("rev-parse", "HEAD^{tree}").stdout.strip()
    dirty = git("status", "--porcelain=v1", "--untracked-files=all").stdout
    if revision != expected_revision or tree != expected_tree:
        raise ConformanceError("provider checkout differs from the registered commit/tree")
    if dirty:
        raise ConformanceError("provider checkout must be clean before conformance testing")
    receipt: dict[str, Any] = {
        "revision": revision,
        "tree": tree,
        "worktree_clean": True,
    }
    if expected_archive_sha256 is not None:
        archive = git("archive", "--format=tar", "HEAD", text=False).stdout
        archive_sha256 = hashlib.sha256(archive).hexdigest()
        if archive_sha256 != expected_archive_sha256:
            raise ConformanceError("provider git archive digest differs from the contract")
        receipt["archive_sha256"] = archive_sha256
    return receipt


def _parse_junit(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    failed = sum(case.find("failure") is not None for case in cases)
    errors = sum(case.find("error") is not None for case in cases)
    skipped = sum(case.find("skipped") is not None for case in cases)
    return {
        "tests": len(cases),
        "passed": len(cases) - failed - errors - skipped,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
    }


def _summary_from_text(text: str) -> dict[str, int]:
    summary = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "xfailed": 0,
        "xpassed": 0,
    }
    for match in SUMMARY_RE.finditer(text):
        label = match.group("label")
        if label == "error":
            label = "errors"
        summary[label] = int(match.group("count"))
    return summary


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: float,
) -> tuple[int, str, float, bool]:
    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds,
        )
        return completed.returncode, completed.stdout, time.monotonic() - start, False
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        return 124, output, time.monotonic() - start, True


def _pytest_group(
    name: str,
    tests: tuple[str, ...],
    *,
    cwd: Path,
    env: dict[str, str],
    work_root: Path,
    timeout_seconds: float,
    extra_args: tuple[str, ...] = (),
) -> tuple[dict[str, Any], bytes]:
    junit = work_root / f"{name}.xml"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        f"--basetemp={work_root / ('pytest-' + name)}",
        f"--junitxml={junit}",
        *extra_args,
        *tests,
    ]
    returncode, output, elapsed, timed_out = _run(
        command, cwd=cwd, env=env, timeout_seconds=timeout_seconds
    )
    summary = _parse_junit(junit) if junit.is_file() else _summary_from_text(output)
    result = {
        "group": name,
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 6),
        "summary": summary,
        "status": "PASS" if returncode == 0 and not timed_out else "FAIL",
    }
    return result, output.encode(errors="replace")


HINDSIGHT_TIMEOUT_PROBE = """
import json
import time
from plugins.memory.hindsight import HindsightMemoryProvider

p = HindsightMemoryProvider()
p._bank_id = "probe-bank"
p._pending_retain_ops.add("probe-op")

def slow_status(_bank_id, _op_id):
    time.sleep(0.25)
    return False

p._is_retain_op_complete = slow_status
budget = 0.05
start = time.monotonic()
p._wait_for_server_retain_ops(start + budget, budget)
elapsed = time.monotonic() - start
print(json.dumps({"budget_seconds": budget, "elapsed_seconds": elapsed}))
if elapsed > 0.15:
    raise SystemExit(1)
"""


def _hindsight_probe(
    *, env: dict[str, str], cwd: Path
) -> tuple[dict[str, Any], bytes]:
    command = [sys.executable, "-c", HINDSIGHT_TIMEOUT_PROBE]
    returncode, output, elapsed, timed_out = _run(
        command, cwd=cwd, env=env, timeout_seconds=5.0
    )
    parsed: dict[str, Any] = {}
    for line in output.splitlines():
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "elapsed_seconds" in candidate:
            parsed = candidate
    result = {
        "group": "hindsight-strict-timeout-probe",
        "command": [sys.executable, "-c", "<registered-timeout-probe>"],
        "returncode": returncode,
        "timed_out": timed_out,
        "elapsed_seconds": round(elapsed, 6),
        "measurement": parsed,
        "status": "PASS" if returncode == 0 and not timed_out else "FAIL",
    }
    return result, output.encode(errors="replace")


MEMORI_DISCOVERY_CODE = """
import json
from plugins.memory import list_memory_provider_names, load_memory_provider

expected = [
    "byterover", "hindsight", "holographic", "honcho", "mem0",
    "memori", "openviking", "retaindb", "supermemory",
]
names = list_memory_provider_names()
assert names == expected, (names, expected)
provider = load_memory_provider("memori", register_skills=False)
assert provider is not None and provider.name == "memori"
tools = [schema["name"] for schema in provider.get_tool_schemas()]
expected_tools = [
    "memori_recall", "memori_recall_summary", "memori_compaction",
    "memori_quota", "memori_signup", "memori_feedback",
]
assert tools == expected_tools, tools
print(json.dumps({"providers": names, "provider": provider.name, "tools": tools}))
"""


def _memori_discovery(
    *,
    hermes_root: Path,
    env: dict[str, str],
    work_root: Path,
) -> tuple[dict[str, Any], bytes]:
    adjacent_installer = Path(sys.executable).with_name("hermes-memori")
    installer = (
        str(adjacent_installer)
        if adjacent_installer.is_file() and not adjacent_installer.is_symlink()
        else shutil.which("hermes-memori")
    )
    if installer is None:
        return {
            "group": "memori-install-discovery",
            "returncode": 127,
            "timed_out": False,
            "elapsed_seconds": 0.0,
            "status": "FAIL",
            "error": "hermes-memori executable is absent",
        }, b"hermes-memori executable is absent\n"
    hermes_home = work_root / "hermes-home"
    install_command = [installer, "--hermes-home", str(hermes_home), "install"]
    rc1, output1, elapsed1, timeout1 = _run(
        install_command, cwd=hermes_root, env=env, timeout_seconds=10.0
    )
    discovery_env = dict(env)
    discovery_env["HERMES_HOME"] = str(hermes_home)
    discovery_env["PYTHONPATH"] = str(hermes_root)
    discovery_command = [sys.executable, "-c", MEMORI_DISCOVERY_CODE]
    rc2, output2, elapsed2, timeout2 = _run(
        discovery_command,
        cwd=hermes_root,
        env=discovery_env,
        timeout_seconds=20.0,
    )
    returncode = rc1 or rc2
    result = {
        "group": "memori-install-discovery",
        "command": [install_command, [sys.executable, "-c", "<registered-discovery>"]],
        "returncode": returncode,
        "timed_out": timeout1 or timeout2,
        "elapsed_seconds": round(elapsed1 + elapsed2, 6),
        "status": "PASS" if returncode == 0 and not (timeout1 or timeout2) else "FAIL",
    }
    return result, (output1 + output2).encode(errors="replace")


def run_matrix(
    *,
    experiment: Path,
    hermes_root: Path,
    memori_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    contract, experiment_sha256 = load_and_validate_experiment(experiment)
    hermes_root = _regular_directory(hermes_root, "Hermes root")
    memori_root = _regular_directory(memori_root, "Memori root")
    hermes_receipt = _git_source_receipt(
        hermes_root,
        expected_revision=contract["sources"]["hermes"]["revision"],
        expected_tree=contract["sources"]["hermes"]["tree"],
        expected_archive_sha256=contract["sources"]["hermes"]["archive_sha256"],
    )
    memori_receipt = _git_source_receipt(
        memori_root,
        expected_revision=contract["sources"]["memori"]["revision"],
        expected_tree=contract["sources"]["memori"]["tree"],
    )
    runtime_image = os.environ.get("COTCODEC_CONTAINER_IMAGE")
    if runtime_image != EXPECTED_IMAGE:
        raise ConformanceError(
            "COTCODEC_CONTAINER_IMAGE must equal the registered digest-pinned image"
        )
    output_dir = _prepare_output(output_dir)
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(mode=0o700)
    work_root = Path(tempfile.mkdtemp(prefix="hermes-provider-", dir="/tmp"))
    os.chmod(work_root, 0o700)
    env = {
        "HOME": str(work_root / "home"),
        "HERMES_HOME": str(work_root / "hermes"),
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(hermes_root),
    }
    (work_root / "home").mkdir()
    results: list[dict[str, Any]] = []
    try:
        for provider, tests in HERMES_GROUPS.items():
            result, log = _pytest_group(
                provider,
                tests,
                cwd=hermes_root,
                env=env,
                work_root=work_root,
                timeout_seconds=180.0,
            )
            _write_new(logs_dir / f"{provider}.log", log)
            results.append(result)

        result, log = _pytest_group(
            "common",
            COMMON_GROUP,
            cwd=hermes_root,
            env=env,
            work_root=work_root,
            timeout_seconds=60.0,
        )
        _write_new(logs_dir / "common.log", log)
        results.append(result)

        memori_integration = memori_root / "integrations" / "hermes"
        result, log = _pytest_group(
            "memori",
            tuple(
                str(path)
                for path in sorted((memori_root / MEMORI_TEST_DIR).glob("test_*.py"))
            ),
            cwd=memori_root,
            env={
                **env,
                "PYTHONPATH": (
                    str(memori_integration / "src") + ":" + str(hermes_root)
                ),
            },
            work_root=work_root,
            timeout_seconds=60.0,
            extra_args=(
                "-o",
                "addopts=",
                f"--rootdir={memori_integration}",
                f"--confcutdir={memori_integration / 'tests'}",
            ),
        )
        _write_new(logs_dir / "memori.log", log)
        results.append(result)

        result, log = _memori_discovery(
            hermes_root=hermes_root, env=env, work_root=work_root
        )
        _write_new(logs_dir / "memori-install-discovery.log", log)
        results.append(result)

        result, log = _hindsight_probe(env=env, cwd=hermes_root)
        _write_new(logs_dir / "hindsight-strict-timeout-probe.log", log)
        results.append(result)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    strict_pass = all(result["status"] == "PASS" for result in results)
    report = {
        "schema_version": 1,
        "study": "hermes-memory-provider-conformance-v1",
        "experiment_sha256": experiment_sha256,
        "scientific_result": False,
        "publication_ready": False,
        "runtime": {
            "container_image": runtime_image,
            "expected_container_image": EXPECTED_IMAGE,
            "python": sys.version,
            "platform": platform.platform(),
            "network_contract": "none",
        },
        "source_contract": contract["sources"],
        "source_receipts": {"hermes": hermes_receipt, "memori": memori_receipt},
        "provider_roster": EXPECTED_ROSTER,
        "results": results,
        "status": "PASS" if strict_pass else "FAIL",
        "evidence_role": "cpu-provider-contract-only",
    }
    report_bytes = _canonical_json(report)
    _write_new(output_dir / "report.json", report_bytes)
    manifest = {
        "schema_version": 1,
        "study": report["study"],
        "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
        "experiment_sha256": experiment_sha256,
        "log_sha256s": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(logs_dir.iterdir())
        },
        "status": report["status"],
    }
    _write_new(output_dir / "manifest.json", _canonical_json(manifest))
    directory_fd = os.open(output_dir, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, default=DEFAULT_EXPERIMENT)
    parser.add_argument("--hermes-root", type=Path, required=True)
    parser.add_argument("--memori-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = run_matrix(
        experiment=args.experiment,
        hermes_root=args.hermes_root,
        memori_root=args.memori_root,
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": report["status"], "results": report["results"]}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
