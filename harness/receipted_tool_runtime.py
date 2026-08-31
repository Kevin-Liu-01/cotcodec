"""Tool runtime that makes expected SQLite constraint failures observable."""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any, Protocol

from harness.agent_loop import ToolCall
from harness.live_canary import SQLiteCanaryToolRuntime, _validate_arguments
from harness.run_state import canonical_json


class _Delegate(Protocol):
    async def execute(self, call: ToolCall) -> dict[str, Any]: ...

    def close_and_receipt(self) -> dict[str, Any]: ...


class ReceiptedSQLiteCanaryToolRuntime:
    """Return one stable error union for admitted SQLite constraint failures."""

    identity = "sqlite-canary-tools-receipted-errors-v2"
    contract = {
        "schema_version": 1,
        "identity": identity,
        "delegate": SQLiteCanaryToolRuntime.identity,
        "native_success_results": True,
        "caught_exception": "sqlite3.IntegrityError",
        "unexpected_exceptions": "propagate",
        "implicit_retries": 0,
        "idempotent_success_rewrite": False,
        "record_every_attempt": True,
    }

    def __init__(self, delegate: _Delegate | None = None) -> None:
        self.delegate = delegate or SQLiteCanaryToolRuntime()
        self.attempts: list[dict[str, Any]] = []
        self.closed = False

    async def execute(self, call: ToolCall) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("receipted tool runtime is closed")
        arguments = _validate_arguments(call.name, call.arguments)
        try:
            result = await self.delegate.execute(call)
        except sqlite3.IntegrityError:
            connection = getattr(self.delegate, "connection", None)
            if connection is None:
                raise RuntimeError("SQLite delegate has no rollback connection") from None
            connection.rollback()
            result = {
                "ok": False,
                "error": {
                    "code": "sqlite_constraint_violation",
                    "tool": call.name,
                    "message": "tool mutation violated a uniqueness constraint",
                    "retryable": False,
                },
            }
            self.attempts.append(
                {
                    "name": call.name,
                    "arguments": arguments,
                    "status": "error",
                    "result": result,
                }
            )
            return result
        self.attempts.append(
            {
                "name": call.name,
                "arguments": arguments,
                "status": "success",
                "result": result,
            }
        )
        return result

    def close_and_receipt(self) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("receipted tool runtime is already closed")
        self.closed = True
        delegate_receipt = self.delegate.close_and_receipt()
        attempt_count = len(self.attempts)
        success_count = sum(item["status"] == "success" for item in self.attempts)
        error_count = sum(item["status"] == "error" for item in self.attempts)
        projection = {
            "attempt_count": attempt_count,
            "success_count": success_count,
            "error_count": error_count,
            "attempts": self.attempts,
            "delegate_receipt": delegate_receipt,
        }
        return {
            "schema_version": 1,
            "identity": self.identity,
            **projection,
            "receipt_sha256": hashlib.sha256(
                canonical_json(projection).encode()
            ).hexdigest(),
        }
