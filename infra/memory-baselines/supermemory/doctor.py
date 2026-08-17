#!/usr/bin/env python3
"""Black-box lifecycle doctor for the pinned Supermemory local binary."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

STATE_ROOT = Path("/state/supermemory")
JOURNAL_PATH = Path("/state/doctor-journal.json")
RECOVERY_JOURNAL_PATH = Path("/state/recovery-journal.json")
MODEL_SOURCE = Path("/opt/supermemory-models")
SERVER = Path("/usr/local/bin/supermemory-server")
BASE_URL = "http://127.0.0.1:6767"

CONTAINER_A = "cotcodec-supermemory-doctor-a"
CONTAINER_B = "cotcodec-supermemory-doctor-b"
CANARY_A_V1 = "COTCODEC_SUPERMEMORY_A prefers cobalt tea"
CANARY_A_V2 = "COTCODEC_SUPERMEMORY_A prefers amber tea"
CANARY_B = "COTCODEC_SUPERMEMORY_B stores indigo maps"
CANARY_RECOVERY_A = "COTCODEC_SUPERMEMORY_RECOVERY_A keeps silver keys"
CANARY_RECOVERY_B = "COTCODEC_SUPERMEMORY_RECOVERY_B keeps violet keys"
RECOVERY_CONTAINER_A = "cotcodec-supermemory-recovery-a"
RECOVERY_CONTAINER_B = "cotcodec-supermemory-recovery-b"

EXPECTED_MODEL_FILES = {
    "Xenova/bge-base-en-v1.5/config.json": (
        "d83c21fa7366994560727112ef0a31d8a2ec1c280c2a3e66326fdb877f64c91e"
    ),
    "Xenova/bge-base-en-v1.5/onnx/model_quantized.onnx": (
        "c9729cc84cbd0e9fecc759505d2be65916c9fe05222d7ea26c65fcb3382af38d"
    ),
    "Xenova/bge-base-en-v1.5/tokenizer.json": (
        "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66"
    ),
    "Xenova/bge-base-en-v1.5/tokenizer_config.json": (
        "9261e7d79b44c8195c1cada2b453e55b00aeb81e907a6664974b4d7776172ab3"
    ),
}


class DoctorError(RuntimeError):
    """Raised when the binary violates the registered lifecycle contract."""


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def _write_once(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise DoctorError(f"short write: {path}")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _strict_object(data: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise DoctorError(f"{label} contains non-finite value {value}")

    try:
        payload = json.loads(data, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoctorError(f"{label} is not strict JSON") from exc
    if not isinstance(payload, dict):
        raise DoctorError(f"{label} must be a JSON object")
    return payload


def _copy_and_verify_model_cache() -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative, expected in EXPECTED_MODEL_FILES.items():
        source = MODEL_SOURCE / relative
        if not source.is_file() or source.is_symlink():
            raise DoctorError(f"missing image model artifact: {relative}")
        source_sha = _sha_path(source)
        if source_sha != expected:
            raise DoctorError(f"image model artifact drifted: {relative}")
        destination = STATE_ROOT / "models" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if not destination.is_file() or destination.is_symlink():
                raise DoctorError(f"unsafe persisted model artifact: {relative}")
        else:
            shutil.copyfile(source, destination)
            destination.chmod(0o400)
        persisted_sha = _sha_path(destination)
        if persisted_sha != expected:
            raise DoctorError(f"persisted model artifact drifted: {relative}")
        actual[relative] = persisted_sha
    return actual


def _redacted_log(log_path: Path) -> str:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    words = []
    for word in text.split():
        words.append("<redacted-api-key>" if word.startswith("sm_") else word)
    return " ".join(words)


def _start_server() -> tuple[subprocess.Popen[bytes], Path]:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    _copy_and_verify_model_cache()
    descriptor, raw_path = tempfile.mkstemp(prefix="supermemory-server-", suffix=".log")
    os.close(descriptor)
    log_path = Path(raw_path)
    log_file = log_path.open("wb")
    env = {
        **os.environ,
        "SUPERMEMORY_DATA_DIR": str(STATE_ROOT),
        "SUPERMEMORY_DISABLE_TELEMETRY": "1",
        "SUPERMEMORY_NO_UPDATE_CHECK": "1",
        "SUPERMEMORY_NO_OPEN": "1",
        "SUPERMEMORY_NO_COLOR": "1",
        "SUPERMEMORY_NO_STARTUP_ANIMATION": "1",
        "SUPERMEMORY_RUN_CRONS_AT_BOOT": "0",
        "OPENAI_API_KEY": "cotcodec-loopback-only",
        "OPENAI_BASE_URL": "http://127.0.0.1:1/v1",
        "OPENAI_MODEL": "cotcodec-unused",
        "OPENAI_FAST_MODEL": "cotcodec-unused",
        "OPENAI_TEXT_MODEL": "cotcodec-unused",
    }
    process = subprocess.Popen(
        [str(SERVER)],
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
    )
    log_file.close()
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise DoctorError(
                f"Supermemory exited during startup: {_redacted_log(log_path)}"
            )
        try:
            with urlopen(f"{BASE_URL}/", timeout=1) as response:
                if response.status == 200:
                    response.read(1)
                    return process, log_path
        except (HTTPError, URLError, TimeoutError):
            pass
        time.sleep(0.1)
    process.kill()
    process.wait(timeout=5)
    raise DoctorError(f"Supermemory startup timed out: {_redacted_log(log_path)}")


def _stop_server(process: subprocess.Popen[bytes], *, crash: bool) -> None:
    if process.poll() is not None:
        return
    if crash:
        process.kill()
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _request(method: str, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        f"{BASE_URL}{endpoint}",
        data=json.dumps(body, separators=(",", ":"), sort_keys=True).encode(),
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload = _strict_object(response.read(), f"{method} {endpoint}")
            return {"status": response.status, "body": payload}
    except HTTPError as exc:
        payload = _strict_object(exc.read(), f"{method} {endpoint} error")
        raise DoctorError(
            f"{method} {endpoint} returned {exc.code}: {payload}"
        ) from exc


def _entries(container: str) -> dict[str, Any]:
    return _request(
        "POST",
        "/v4/memories/list",
        {"containerTags": [container], "includeHistory": True, "limit": 100},
    )


def _search(container: str, query: str) -> dict[str, Any]:
    return _request(
        "POST",
        "/v4/search",
        {"q": query, "containerTag": container, "searchMode": "memories"},
    )


def _entry_contents(result: dict[str, Any]) -> list[str]:
    rows = result["body"].get("memoryEntries")
    if not isinstance(rows, list):
        raise DoctorError("memory list response is malformed")
    return [row.get("memory") for row in rows if isinstance(row, dict)]


def _search_contents(result: dict[str, Any]) -> list[str]:
    rows = result["body"].get("results")
    if not isinstance(rows, list):
        raise DoctorError("search response is malformed")
    return [row.get("memory") for row in rows if isinstance(row, dict)]


def _phase_prepare() -> dict[str, Any]:
    if JOURNAL_PATH.exists():
        raise DoctorError("prepare requires a clean doctor journal")
    process, log_path = _start_server()
    try:
        create_a = _request(
            "POST",
            "/v4/memories",
            {
                "containerTag": CONTAINER_A,
                "memories": [
                    {
                        "content": CANARY_A_V1,
                        "isStatic": False,
                        "metadata": {"source_event_id": "event-a-1"},
                    }
                ],
            },
        )
        create_b = _request(
            "POST",
            "/v4/memories",
            {
                "containerTag": CONTAINER_B,
                "memories": [
                    {
                        "content": CANARY_B,
                        "isStatic": True,
                        "metadata": {"source_event_id": "event-b-1"},
                    }
                ],
            },
        )
        memory_a = create_a["body"].get("memories", [])
        memory_b = create_b["body"].get("memories", [])
        if len(memory_a) != 1 or len(memory_b) != 1:
            raise DoctorError("direct memory create did not return exactly one row")
        root_a = memory_a[0].get("id")
        id_b = memory_b[0].get("id")
        if not isinstance(root_a, str) or not isinstance(id_b, str):
            raise DoctorError("created memory IDs are missing")
        update_a = _request(
            "PATCH",
            "/v4/memories",
            {
                "id": root_a,
                "containerTag": CONTAINER_A,
                "newContent": CANARY_A_V2,
                "metadata": {
                    "source_event_id": "event-a-2",
                    "supersedes": "event-a-1",
                },
            },
        )
        current_a = update_a["body"].get("id")
        if not isinstance(current_a, str):
            raise DoctorError("versioned update did not return a new memory ID")
        list_a = _entries(CONTAINER_A)
        list_b = _entries(CONTAINER_B)
        search_a = _search(CONTAINER_A, CANARY_A_V2)
        search_b = _search(CONTAINER_B, CANARY_B)
        if _entry_contents(list_a) != [CANARY_A_V2]:
            raise DoctorError("container A latest memory is incorrect")
        if _entry_contents(list_b) != [CANARY_B]:
            raise DoctorError("container B memory is incorrect")
        if CANARY_A_V2 not in _search_contents(search_a):
            raise DoctorError("container A cannot retrieve its updated memory")
        if CANARY_B not in _search_contents(search_b):
            raise DoctorError("container B cannot retrieve its memory")
        if CANARY_A_V1 in _search_contents(search_a):
            raise DoctorError("superseded memory remained searchable")
        row_a = list_a["body"]["memoryEntries"][0]
        history = row_a.get("history")
        if (
            row_a.get("version") != 2
            or not isinstance(history, list)
            or len(history) != 1
            or history[0].get("memory") != CANARY_A_V1
        ):
            raise DoctorError("version history is incomplete")
        _write_once(
            JOURNAL_PATH,
            _json_bytes(
                {
                    "root_a": root_a,
                    "current_a": current_a,
                    "id_b": id_b,
                    "document_a": create_a["body"].get("documentId"),
                    "document_b": create_b["body"].get("documentId"),
                }
            ),
        )
        result = {
            "phase": "prepare",
            "crash_injected_after_committed_update": True,
            "checks": {
                "direct_create": True,
                "versioned_update": True,
                "superseded_not_searchable": True,
                "version_history_preserved": True,
                "tenant_a_retrieval": True,
                "tenant_b_retrieval": True,
            },
            "response_sha256": {
                "create_a": _sha_bytes(_json_bytes(create_a)),
                "create_b": _sha_bytes(_json_bytes(create_b)),
                "update_a": _sha_bytes(_json_bytes(update_a)),
                "list_a": _sha_bytes(_json_bytes(list_a)),
                "list_b": _sha_bytes(_json_bytes(list_b)),
            },
        }
    finally:
        _stop_server(process, crash=True)
        log_path.unlink(missing_ok=True)
    return result


def _load_journal() -> dict[str, Any]:
    if not JOURNAL_PATH.is_file() or JOURNAL_PATH.is_symlink():
        raise DoctorError("doctor journal is missing")
    return _strict_object(JOURNAL_PATH.read_bytes(), "doctor journal")


def _phase_restart() -> dict[str, Any]:
    _load_journal()
    process, log_path = _start_server()
    try:
        list_a = _entries(CONTAINER_A)
        list_b = _entries(CONTAINER_B)
        search_a = _search(CONTAINER_A, CANARY_A_V2)
        search_b = _search(CONTAINER_B, CANARY_B)
        cross_a = _search(CONTAINER_A, CANARY_B)
        cross_b = _search(CONTAINER_B, CANARY_A_V2)
        list_a_contents = _entry_contents(list_a)
        list_b_contents = _entry_contents(list_b)
        search_a_contents = _search_contents(search_a)
        search_b_contents = _search_contents(search_b)
        survived_a = list_a_contents == [CANARY_A_V2] and CANARY_A_V2 in search_a_contents
        survived_b = list_b_contents == [CANARY_B] and CANARY_B in search_b_contents
        history_survived = False
        if survived_a:
            row_a = list_a["body"]["memoryEntries"][0]
            history = row_a.get("history")
            history_survived = (
                row_a.get("version") == 2
                and isinstance(history, list)
                and len(history) == 1
                and history[0].get("memory") == CANARY_A_V1
            )
        if CANARY_B in _search_contents(cross_a) or CANARY_A_V2 in _search_contents(
            cross_b
        ):
            raise DoctorError("cross-container memory disclosure reproduced")
        recovery_a = _request(
            "POST",
            "/v4/memories",
            {
                "containerTag": RECOVERY_CONTAINER_A,
                "memories": [{"content": CANARY_RECOVERY_A, "isStatic": False}],
            },
        )
        recovery_b = _request(
            "POST",
            "/v4/memories",
            {
                "containerTag": RECOVERY_CONTAINER_B,
                "memories": [{"content": CANARY_RECOVERY_B, "isStatic": False}],
            },
        )
        recovery_a_rows = recovery_a["body"].get("memories", [])
        recovery_b_rows = recovery_b["body"].get("memories", [])
        if len(recovery_a_rows) != 1 or len(recovery_b_rows) != 1:
            raise DoctorError("recovery memory create did not return one row per tenant")
        recovery_a_id = recovery_a_rows[0].get("id")
        recovery_b_id = recovery_b_rows[0].get("id")
        if not isinstance(recovery_a_id, str) or not isinstance(recovery_b_id, str):
            raise DoctorError("recovery memory IDs are missing")
        _write_once(
            RECOVERY_JOURNAL_PATH,
            _json_bytes({"recovery_a_id": recovery_a_id, "recovery_b_id": recovery_b_id}),
        )
        result = {
            "phase": "restart",
            "checks": {
                "acknowledged_tenant_a_survives_sigkill": survived_a,
                "acknowledged_tenant_b_survives_sigkill": survived_b,
                "version_history_survives_sigkill": history_survived,
                "cross_tenant_plaintext_disclosure": False,
                "recovery_pair_committed_before_graceful_stop": True,
            },
            "counts": {
                "tenant_a_latest_after_sigkill": len(list_a_contents),
                "tenant_b_latest_after_sigkill": len(list_b_contents),
            },
        }
    finally:
        _stop_server(process, crash=False)
        log_path.unlink(missing_ok=True)
    return result


def _plaintext_hits() -> list[dict[str, Any]]:
    needles = (
        CANARY_A_V1.encode(),
        CANARY_A_V2.encode(),
        CANARY_B.encode(),
        CANARY_RECOVERY_A.encode(),
        CANARY_RECOVERY_B.encode(),
    )
    hits: list[dict[str, Any]] = []
    for path in sorted(STATE_ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink() or "models" in path.parts:
            continue
        data = path.read_bytes()
        matched = [_sha_bytes(needle) for needle in needles if needle in data]
        if matched:
            hits.append(
                {
                    "path": path.relative_to(STATE_ROOT).as_posix(),
                    "canary_sha256": matched,
                }
            )
    return hits


def _state_manifest() -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for path in sorted(STATE_ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink() or "models" in path.parts:
            continue
        relative = path.relative_to(STATE_ROOT).as_posix()
        manifest[relative] = {"bytes": path.stat().st_size, "sha256": _sha_path(path)}
    return manifest


def _phase_forget() -> dict[str, Any]:
    _load_journal()
    if not RECOVERY_JOURNAL_PATH.is_file() or RECOVERY_JOURNAL_PATH.is_symlink():
        raise DoctorError("recovery journal is missing")
    recovery_journal = _strict_object(
        RECOVERY_JOURNAL_PATH.read_bytes(), "recovery journal"
    )
    current_a = recovery_journal.get("recovery_a_id")
    if not isinstance(current_a, str):
        raise DoctorError("recovery journal lacks container A memory ID")
    process, log_path = _start_server()
    try:
        before_a = _entries(RECOVERY_CONTAINER_A)
        before_b = _entries(RECOVERY_CONTAINER_B)
        if _entry_contents(before_a) != [CANARY_RECOVERY_A]:
            raise DoctorError("gracefully persisted recovery A memory is missing")
        if _entry_contents(before_b) != [CANARY_RECOVERY_B]:
            raise DoctorError("gracefully persisted recovery B memory is missing")
        forgotten = _request(
            "DELETE",
            "/v4/memories",
            {
                "id": current_a,
                "containerTag": RECOVERY_CONTAINER_A,
                "reason": "cotcodec-physical-purge-admission-probe",
            },
        )
        if forgotten["body"].get("forgotten") is not True:
            raise DoctorError("soft forget did not acknowledge the memory")
        search_a = _search(RECOVERY_CONTAINER_A, CANARY_RECOVERY_A)
        list_a = _entries(RECOVERY_CONTAINER_A)
        list_b = _entries(RECOVERY_CONTAINER_B)
        if _search_contents(search_a) or _entry_contents(list_a):
            raise DoctorError("soft-forgotten memory remains normally visible")
        if _entry_contents(list_b) != [CANARY_RECOVERY_B]:
            raise DoctorError("forget in container A changed container B")
    finally:
        _stop_server(process, crash=False)
        log_path.unlink(missing_ok=True)
    plaintext_hits = _plaintext_hits()
    state_manifest = _state_manifest()
    return {
        "phase": "forget",
        "checks": {
            "soft_forget_excludes_normal_search": True,
            "soft_forget_excludes_normal_list": True,
            "other_tenant_survives": True,
            "graceful_restart_persists_acknowledged_pair": True,
            "native_tenant_scoped_physical_purge_available": False,
            "provider_plaintext_at_rest_detected": bool(plaintext_hits),
        },
        "plaintext_hits": plaintext_hits,
        "state_file_count": len(state_manifest),
        "state_manifest_sha256": _sha_bytes(_json_bytes(state_manifest)),
        "response_sha256": _sha_bytes(_json_bytes(forgotten)),
    }


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "restart", "forget"}:
        raise SystemExit("usage: doctor.py {prepare|restart|forget}")
    phase = sys.argv[1]
    if phase == "prepare":
        result = _phase_prepare()
    elif phase == "restart":
        result = _phase_restart()
    else:
        result = _phase_forget()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
