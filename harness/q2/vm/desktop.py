"""OSWorld ``DesktopEnv.step`` and ``PythonController`` behaviour, on the standard library.

The suite's executor runs through the same transport Stage 1 uses: OSWorld
``b138d348`` ``DesktopEnv.step(action, pause)`` with ``action_space ==
"pyautogui"``. For a command string that is
``PythonController.execute_python_command``: POST ``/execute`` with
``{"command": ["python", "-c", PYAUTOGUI_PKGS_PREFIX.format(command=...)],
"shell": false}`` (120 s timeout, up to three attempts 5 s apart, a read
timeout ends the attempts); then ``time.sleep(pause)``; then ``_get_obs``:
``/screenshot`` (10 s timeout, three attempts 5 s apart, PNG or JPEG magic
required) and, when ``require_a11y_tree``, ``/accessibility`` (three attempts
5 s apart, the ``AT`` field of the JSON reply). ``WAIT``, ``FAIL`` and ``DONE``
send nothing and sleep ``pause`` before the observation.

The runner imports OSWorld nothing (its client needs ``requests``); this
module reproduces those calls and records their HTTP status and timing, which
the preregistration's infrastructure-failure rule needs (section 6.1).
``PYAUTOGUI_PKGS_PREFIX`` is copied from
``desktop_env/controllers/python.py`` at ``b138d348`` (Apache-2.0, Copyright
the OSWorld authors).
"""

from __future__ import annotations

import json
import time
from typing import Any

from harness.q2.vm.guest_http import GuestClient, GuestError

PYAUTOGUI_PKGS_PREFIX = (
    "import pyautogui; import time; import platform; "
    "pyautogui.FAILSAFE = False; "
    "_osworld_shift_chars = '~!@#$%^&*()_+' + chr(123) + chr(125) + '|:\"<>?'; "
    "_osworld_linux_shift_chars = '~!@#$%^&*()_+' + chr(123) + chr(125) + '|:\">?'; "
    "pyautogui.isShiftCharacter = lambda character: character.isupper() or "
    "character in (_osworld_linux_shift_chars if platform.system() == 'Linux' "
    "else _osworld_shift_chars); "
    "{command}"
)
RETRY_TIMES = 3
RETRY_INTERVAL_S = 5.0
EXECUTE_TIMEOUT_S = 120.0
SCREENSHOT_TIMEOUT_S = 10.0
ACCESSIBILITY_TIMEOUT_S = 120.0
INFRA_EXECUTE_S = 30.0  # preregistration 6.1: no HTTP 200 within 30 s is an infrastructure failure


def _image_ok(payload: bytes) -> bool:
    return payload[:8] == b"\x89PNG\r\n\x1a\n" or payload[:3] == b"\xff\xd8\xff"


def execute_python_command(client: GuestClient, command: str) -> dict[str, Any]:
    argv = ["python", "-c", PYAUTOGUI_PKGS_PREFIX.format(command=command)]
    body = json.dumps({"command": argv, "shell": False}).encode("utf-8")
    attempts: list[dict[str, Any]] = []
    for attempt in range(RETRY_TIMES):
        started = time.monotonic()
        try:
            status, payload, elapsed = client._request(
                "POST", "/execute", body, "application/json", timeout=EXECUTE_TIMEOUT_S
            )
        except GuestError as exc:
            attempts.append(
                {"error": str(exc)[:200], "elapsed_s": round(time.monotonic() - started, 4)}
            )
            if "timed out" in str(exc).lower():
                break
            time.sleep(RETRY_INTERVAL_S)
            continue
        attempts.append({"status": status, "elapsed_s": round(elapsed, 4)})
        if status == 200:
            try:
                result = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                result = {"status": "non-json"}
            return {"ok": True, "attempts": attempts, "result": result}
        if attempt < RETRY_TIMES - 1:
            time.sleep(RETRY_INTERVAL_S)
    return {"ok": False, "attempts": attempts, "result": None}


def get_screenshot(client: GuestClient) -> tuple[bytes | None, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(RETRY_TIMES):
        try:
            status, payload, elapsed = client.screenshot(timeout=SCREENSHOT_TIMEOUT_S)
            attempts.append(
                {"status": status, "elapsed_s": round(elapsed, 4), "bytes": len(payload)}
            )
            if status == 200 and _image_ok(payload):
                return payload, attempts
        except GuestError as exc:
            attempts.append({"error": str(exc)[:200]})
        if attempt < RETRY_TIMES - 1:
            time.sleep(RETRY_INTERVAL_S)
    return None, attempts


def get_accessibility_tree(client: GuestClient) -> tuple[str | None, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(RETRY_TIMES):
        try:
            status, payload, elapsed = client._request(
                "GET", "/accessibility", timeout=ACCESSIBILITY_TIMEOUT_S
            )
            attempts.append(
                {"status": status, "elapsed_s": round(elapsed, 4), "bytes": len(payload)}
            )
            if status == 200:
                return json.loads(payload.decode("utf-8"))["AT"], attempts
        except (GuestError, ValueError, KeyError) as exc:
            attempts.append({"error": str(exc)[:200]})
        if attempt < RETRY_TIMES - 1:
            time.sleep(RETRY_INTERVAL_S)
    return None, attempts


def step(
    client: GuestClient, action: str, pause: float = 0.0, a11y: bool = False
) -> dict[str, Any]:
    """One ``DesktopEnv.step`` (pyautogui action space): execute, sleep ``pause``, observe."""
    started = time.monotonic()
    record: dict[str, Any] = {
        "action_kind": action if action in ("WAIT", "FAIL", "DONE") else "code"
    }
    if action in ("WAIT", "FAIL", "DONE"):
        if action == "WAIT":
            time.sleep(pause)
    else:
        record["execute"] = execute_python_command(client, action)
    t_exec = time.monotonic()
    time.sleep(pause)
    screenshot, shot_attempts = get_screenshot(client)
    record["screenshot_attempts"] = shot_attempts
    t_shot = time.monotonic()
    if a11y:
        tree, tree_attempts = get_accessibility_tree(client)
        record["accessibility_attempts"] = tree_attempts
        record["accessibility_bytes"] = len(tree) if tree is not None else None
    record["timing_s"] = {
        "execute": round(t_exec - started, 4),
        "screenshot": round(t_shot - t_exec, 4),
        "total": round(time.monotonic() - started, 4),
    }
    record["screenshot_ok"] = screenshot is not None
    record["infra"] = infra_failures(record, a11y)
    record["retried"] = observation_retries(record, a11y)
    return record, screenshot


def infra_failures(record: dict[str, Any], a11y: bool) -> list[str]:
    """Infrastructure failure types of one step (preregistration 6.1).

    ``execute``: the first ``/execute`` attempt is not HTTP 200 within 30 s (a later
    attempt could run the action twice). ``screenshot``: no valid image after
    ``DesktopEnv``'s attempts. ``accessibility`` (screenshot+a11y setting): no tree after
    its attempts. An observation that a retry delivers is what Stage 1 would see; it is
    not a failure and is counted by ``observation_retries`` (reported per campaign).
    """
    out = []
    execute = record.get("execute")
    if execute is not None:
        first = (execute.get("attempts") or [{}])[0]
        if (
            not execute.get("ok")
            or first.get("status") != 200
            or first.get("elapsed_s", 0) > INFRA_EXECUTE_S
        ):
            out.append("execute")
    if not record.get("screenshot_ok"):
        out.append("screenshot")
    if a11y and record.get("accessibility_bytes") is None:
        out.append("accessibility")
    return out


def observation_retries(record: dict[str, Any], a11y: bool) -> list[str]:
    """Observations ``DesktopEnv``'s retries delivered after a failed first attempt."""
    out = []
    shots = record.get("screenshot_attempts") or [{}]
    if record.get("screenshot_ok") and (shots[0].get("status") != 200 or len(shots) > 1):
        out.append("screenshot")
    trees = record.get("accessibility_attempts") or [{}]
    if a11y and record.get("accessibility_bytes") is not None and len(trees) > 1:
        out.append("accessibility")
    return out
