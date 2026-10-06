"""Validated JSON subprocess transport for isolated native memory systems."""

from __future__ import annotations

import contextlib
import json
import os
import selectors
import signal
import subprocess
import tempfile
import threading
import time
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from harness.memory_trials.schema import canonical_json, sha256_text
from harness.memory_trials.systems import (
    MemorySelection,
    MemorySystemReceipt,
    MemorySystemRequest,
)

MAX_SIDECAR_RESPONSE_BYTES = 4 * 1024 * 1024


class MemorySidecarError(RuntimeError):
    """Raised when the isolated adapter violates the wire contract."""


class SubprocessMemorySystem:
    """One-request-per-process adapter suitable for digest-pinned OCI commands."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float = 120.0,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise ValueError("sidecar command must contain non-empty argv strings")
        if timeout_seconds <= 0:
            raise ValueError("sidecar timeout must be positive")
        self._command = tuple(command)
        self._timeout_seconds = timeout_seconds
        self._environment = dict(environment or {})
        self._last_call_elapsed_ms = 0.0
        handshake = self._call("handshake", {})
        try:
            self.receipt = MemorySystemReceipt.model_validate(handshake["receipt"])
        except (KeyError, ValidationError) as exc:
            raise MemorySidecarError("sidecar handshake has an invalid receipt") from exc
        self.identity = self.receipt.system_id

    def _call(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = json.dumps(
            {
                "protocol": "memory-system-v1",
                "operation": operation,
                "payload": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            **self._environment,
        }
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                self._command,
                input=request + "\n",
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
                env=environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise MemorySidecarError(
                f"sidecar timed out during {operation} after {self._timeout_seconds}s"
            ) from exc
        self._last_call_elapsed_ms = (time.perf_counter() - started) * 1000
        if completed.returncode:
            detail = completed.stderr.strip()[-2000:]
            raise MemorySidecarError(
                f"sidecar {operation} failed with exit {completed.returncode}: {detail}"
            )
        encoded = completed.stdout.encode()
        if len(encoded) > MAX_SIDECAR_RESPONSE_BYTES:
            raise MemorySidecarError("sidecar response exceeds the 4 MiB limit")
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if len(lines) != 1:
            raise MemorySidecarError("sidecar must return exactly one JSON response")
        try:
            response = json.loads(lines[0])
        except json.JSONDecodeError as exc:
            raise MemorySidecarError("sidecar returned malformed JSON") from exc
        if not isinstance(response, dict):
            raise MemorySidecarError("sidecar response must be a JSON object")
        if response.get("protocol") != "memory-system-v1":
            raise MemorySidecarError("sidecar changed the protocol version")
        if response.get("operation") != operation:
            raise MemorySidecarError("sidecar response operation mismatch")
        if response.get("ok") is not True:
            result = response.get("result")
            detail = (
                result.get("error")
                if isinstance(result, dict)
                else response.get("error")
            )
            raise MemorySidecarError(f"sidecar rejected {operation}: {detail}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise MemorySidecarError("sidecar result must be a JSON object")
        return result

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        result = self._call("select", request.model_dump(mode="json"))
        try:
            selection = MemorySelection.model_validate(result["selection"])
        except (KeyError, ValidationError) as exc:
            raise MemorySidecarError("sidecar returned an invalid selection") from exc
        if selection.receipt != self.receipt:
            raise MemorySidecarError("sidecar receipt changed after handshake")
        costs = selection.costs.model_copy(
            update={
                "latency_ms": max(
                    selection.costs.latency_ms, self._last_call_elapsed_ms
                )
            }
        )
        payload = {
            "request_id": selection.request_id,
            "evidence": [item.model_dump(mode="json") for item in selection.evidence],
            "costs": costs.model_dump(mode="json"),
            "receipt": selection.receipt.model_dump(mode="json"),
        }
        return MemorySelection(
            **payload,
            selection_sha256=sha256_text(canonical_json(payload)),
        )

    def purge(self, session_scope: str) -> None:
        result = self._call("purge", {"session_scope": session_scope})
        if result.get("purged") is not True:
            raise MemorySidecarError("sidecar did not attest successful purge")

    def inspect(self, session_scope: str) -> dict[str, Any]:
        return self._call("inspect", {"session_scope": session_scope})


class PersistentSubprocessMemorySystem:
    """Long-lived, line-framed sidecar transport for lifecycle experiments.

    The process is started once, handshaken once, and reused across calls. This
    proves transport continuity only; backend persistence and deletion still
    require system-specific conformance receipts.
    """

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float = 120.0,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if not command or any(not isinstance(part, str) or not part for part in command):
            raise ValueError("sidecar command must contain non-empty argv strings")
        if timeout_seconds <= 0:
            raise ValueError("sidecar timeout must be positive")
        self._command = tuple(command)
        self._timeout_seconds = timeout_seconds
        self._last_call_elapsed_ms = 0.0
        self._closed = False
        self._lock = threading.Lock()
        self._stderr = tempfile.TemporaryFile(  # noqa: SIM115 - owned until close()
            mode="w+t", encoding="utf-8"
        )
        process_environment = {
            "PATH": os.environ.get("PATH", ""),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "COTCODEC_MEMORY_PERSISTENT_PROTOCOL": "1",
            **dict(environment or {}),
        }
        self._process = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr,
            text=True,
            bufsize=1,
            env=process_environment,
            start_new_session=True,
        )
        if self._process.stdin is None or self._process.stdout is None:
            self._terminate_process()
            raise MemorySidecarError("persistent sidecar pipes were not created")
        try:
            handshake = self._call("handshake", {})
            self.receipt = MemorySystemReceipt.model_validate(handshake["receipt"])
        except (KeyError, ValidationError) as exc:
            self.close()
            raise MemorySidecarError("sidecar handshake has an invalid receipt") from exc
        except Exception:
            self.close()
            raise
        self.identity = self.receipt.system_id

    @property
    def process_id(self) -> int:
        return self._process.pid

    @property
    def is_running(self) -> bool:
        return not self._closed and self._process.poll() is None

    def _stderr_tail(self) -> str:
        if self._process.poll() is None:
            return ""
        self._stderr.flush()
        self._stderr.seek(0)
        return self._stderr.read()[-2000:]

    def _terminate_process(self) -> None:
        if self._process.poll() is not None:
            return
        try:
            os.killpg(self._process.pid, signal.SIGTERM)
            self._process.wait(timeout=2.0)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            if self._process.poll() is None:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(self._process.pid, signal.SIGKILL)
                self._process.wait(timeout=2.0)

    def _read_response_line(self, operation: str) -> str:
        if self._process.stdout is None:
            raise MemorySidecarError("persistent sidecar stdout is unavailable")
        selector = selectors.DefaultSelector()
        try:
            selector.register(self._process.stdout, selectors.EVENT_READ)
            ready = selector.select(self._timeout_seconds)
        finally:
            selector.close()
        if not ready:
            self._terminate_process()
            raise MemorySidecarError(
                f"sidecar timed out during {operation} after {self._timeout_seconds}s"
            )
        line = self._process.stdout.readline(MAX_SIDECAR_RESPONSE_BYTES + 2)
        if not line:
            returncode = self._process.poll()
            detail = self._stderr_tail()
            raise MemorySidecarError(
                f"sidecar closed stdout during {operation}; exit={returncode}: {detail}"
            )
        if not line.endswith("\n") or len(line.encode()) > MAX_SIDECAR_RESPONSE_BYTES:
            self._terminate_process()
            raise MemorySidecarError("sidecar response exceeds the 4 MiB line limit")
        return line

    def _call(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = canonical_json(
            {
                "protocol": "memory-system-v1",
                "operation": operation,
                "payload": dict(payload),
            }
        )
        with self._lock:
            if self._closed:
                raise MemorySidecarError("persistent sidecar is closed")
            if self._process.poll() is not None:
                raise MemorySidecarError(
                    f"persistent sidecar exited with {self._process.returncode}: "
                    f"{self._stderr_tail()}"
                )
            if self._process.stdin is None:
                raise MemorySidecarError("persistent sidecar stdin is unavailable")
            started = time.perf_counter()
            try:
                self._process.stdin.write(request + "\n")
                self._process.stdin.flush()
            except BrokenPipeError as exc:
                raise MemorySidecarError(
                    f"sidecar pipe broke during {operation}: {self._stderr_tail()}"
                ) from exc
            line = self._read_response_line(operation)
            self._last_call_elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MemorySidecarError("sidecar returned malformed JSON") from exc
        if not isinstance(response, dict):
            raise MemorySidecarError("sidecar response must be a JSON object")
        if response.get("protocol") != "memory-system-v1":
            raise MemorySidecarError("sidecar changed the protocol version")
        if response.get("operation") != operation:
            raise MemorySidecarError("sidecar response operation mismatch")
        result = response.get("result")
        if response.get("ok") is not True:
            detail = result.get("error") if isinstance(result, dict) else None
            raise MemorySidecarError(f"sidecar rejected {operation}: {detail}")
        if not isinstance(result, dict):
            raise MemorySidecarError("sidecar result must be a JSON object")
        return result

    def select(self, request: MemorySystemRequest) -> MemorySelection:
        result = self._call("select", request.model_dump(mode="json"))
        try:
            selection = MemorySelection.model_validate(result["selection"])
        except (KeyError, ValidationError) as exc:
            raise MemorySidecarError("sidecar returned an invalid selection") from exc
        if selection.receipt != self.receipt:
            raise MemorySidecarError("sidecar receipt changed after handshake")
        costs = selection.costs.model_copy(
            update={
                "latency_ms": max(
                    selection.costs.latency_ms, self._last_call_elapsed_ms
                )
            }
        )
        payload = {
            "request_id": selection.request_id,
            "evidence": [item.model_dump(mode="json") for item in selection.evidence],
            "costs": costs.model_dump(mode="json"),
            "receipt": selection.receipt.model_dump(mode="json"),
        }
        return MemorySelection(
            **payload,
            selection_sha256=sha256_text(canonical_json(payload)),
        )

    def purge(self, session_scope: str) -> None:
        result = self._call("purge", {"session_scope": session_scope})
        if result.get("purged") is not True:
            raise MemorySidecarError("sidecar did not attest successful purge")

    def inspect(self, session_scope: str) -> dict[str, Any]:
        return self._call("inspect", {"session_scope": session_scope})

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._process.poll() is None:
                try:
                    result = self._call("shutdown", {})
                    if result.get("shutdown") is not True:
                        raise MemorySidecarError("sidecar did not acknowledge shutdown")
                except MemorySidecarError:
                    self._terminate_process()
                else:
                    try:
                        self._process.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        self._terminate_process()
        finally:
            self._closed = True
            if self._process.stdin is not None:
                self._process.stdin.close()
            if self._process.stdout is not None:
                self._process.stdout.close()
            self._stderr.close()

    def __enter__(self) -> PersistentSubprocessMemorySystem:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
