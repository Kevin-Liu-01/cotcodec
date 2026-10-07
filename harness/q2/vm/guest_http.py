"""Minimal client for the OSWorld guest server (``desktop_env/server/main.py``).

The guest server listens on port 5000 inside the VM. In the default
``none-netns`` layout the VM container has no Docker network at all; the
runner joins its network namespace and reaches the guest at its NAT address
(20.20.20.21) over the in-container ``dockerbridge``. Nothing is published.

Guest-side Python is shipped as base64 in an argv list (``shell=False``), the
same transport the OSWorld controller uses for pyautogui strings, so no shell
expansion can touch it.

Standard library only; Python 3.10 compatible.
"""

from __future__ import annotations

import base64
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# Executes a base64-encoded script with the remaining argv; nothing is shell-parsed.
GUEST_BOOTSTRAP = (
    "import base64,sys;"
    "_src=base64.b64decode(sys.argv[1]).decode('utf-8');"
    "sys.argv=['q2ap_guest']+sys.argv[2:];"
    "exec(compile(_src,'q2ap_guest','exec'),{'__name__':'__main__'})"
)


class GuestError(RuntimeError):
    """The guest server was unreachable or returned an unusable response."""


class GuestClient:
    def __init__(self, host: str, port: int = 5000, timeout: float = 30.0):
        self.base = f"http://{host}:{port}"
        self.host = host
        self.port = port
        self.timeout = timeout

    def tcp_open(self, timeout: float = 1.0) -> bool:
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout):
                return True
        except OSError:
            return False

    def _request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        content_type: str | None = None,
        timeout: float | None = None,
    ) -> tuple[int, bytes, float]:
        request = urllib.request.Request(self.base + path, data=body, method=method)
        if content_type:
            request.add_header("Content-Type", content_type)
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                payload = response.read()
                return response.status, payload, time.monotonic() - started
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), time.monotonic() - started
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise GuestError(f"{method} {path}: {exc}") from exc

    def screenshot(self, timeout: float = 10.0) -> tuple[int, bytes, float]:
        return self._request("GET", "/screenshot", timeout=timeout)

    def platform(self) -> str:
        status, payload, _ = self._request("GET", "/platform", timeout=10.0)
        if status != 200:
            raise GuestError(f"/platform returned {status}")
        return payload.decode("utf-8", errors="replace").strip()

    def accessibility(self, timeout: float = 120.0) -> tuple[int, int, float]:
        status, payload, elapsed = self._request("GET", "/accessibility", timeout=timeout)
        return status, len(payload), elapsed

    def execute(self, argv: list[str], timeout: float = 130.0) -> dict[str, Any]:
        if not argv or not all(isinstance(arg, str) for arg in argv):
            raise GuestError("execute needs a non-empty argv list of strings")
        body = json.dumps({"command": argv, "shell": False}).encode("utf-8")
        status, payload, elapsed = self._request(
            "POST", "/execute", body, "application/json", timeout=timeout
        )
        try:
            result = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GuestError(f"/execute returned non-JSON ({status})") from exc
        if not isinstance(result, dict):
            raise GuestError("/execute returned a non-object")
        result["http_status"] = status
        result["elapsed_s"] = elapsed
        return result

    def launch(self, argv: list[str]) -> tuple[int, str]:
        body = json.dumps({"command": argv, "shell": False}).encode("utf-8")
        status, payload, _ = self._request(
            "POST", "/setup/launch", body, "application/json", timeout=30.0
        )
        return status, payload.decode("utf-8", errors="replace")[:500]

    def read_file(self, path: str) -> tuple[int, bytes]:
        body = urllib.parse.urlencode({"file_path": path}).encode("ascii")
        status, payload, _ = self._request(
            "POST", "/file", body, "application/x-www-form-urlencoded", timeout=30.0
        )
        return status, payload

    def run_script(
        self, source: str, args: list[str] | None = None, python: str = "python3"
    ) -> dict[str, Any]:
        """Run a Python script in the guest; its last stdout line must be one JSON object."""
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        result = self.execute([python, "-c", GUEST_BOOTSTRAP, encoded, *(args or [])])
        if result.get("http_status") != 200 or result.get("returncode") != 0:
            raise GuestError(
                "guest script failed: "
                f"status={result.get('http_status')} rc={result.get('returncode')} "
                f"stderr={str(result.get('error', ''))[-800:]}"
            )
        lines = [line for line in str(result.get("output", "")).splitlines() if line.strip()]
        if not lines:
            raise GuestError("guest script printed nothing")
        try:
            parsed = json.loads(lines[-1])
        except json.JSONDecodeError as exc:
            raise GuestError(f"guest script output is not JSON: {lines[-1][:200]}") from exc
        if not isinstance(parsed, dict):
            raise GuestError("guest script output is not a JSON object")
        parsed["_elapsed_s"] = result.get("elapsed_s")
        return parsed

    def launch_script(
        self, source: str, args: list[str] | None = None, python: str = "python3"
    ) -> tuple[int, str]:
        """Start a long-running guest script in the background (Popen, shell=False)."""
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        return self.launch([python, "-c", GUEST_BOOTSTRAP, encoded, *(args or [])])


def is_png(payload: bytes) -> bool:
    return payload[:8] == PNG_MAGIC


def png_size(payload: bytes) -> tuple[int, int] | None:
    if not is_png(payload) or len(payload) < 24 or payload[12:16] != b"IHDR":
        return None
    return int.from_bytes(payload[16:20], "big"), int.from_bytes(payload[20:24], "big")
