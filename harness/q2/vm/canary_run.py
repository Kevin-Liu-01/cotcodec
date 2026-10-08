"""Runner side of the A6 cross-app canary (one fresh app instance per trial).

``canary_trial`` follows ``canary.yaml``'s procedure: write the fixture and a
fresh profile (``guest/canary.py prepare``), start the app through
``/setup/launch``, wait until its window is active (and, for the
accessibility read-backs, its text object exists), run the entry's actions
through the L0-fixed executor (one ``DesktopEnv.step`` each, screenshot
setting), run the app's finish keys, read the text back, close every process
of the trial, and compare the text with the frozen expectation by code-point
equality. With ``no_input`` the actions and finish keys are skipped and the
read-back must equal the fixture: the read-back validation done before the
inputs addendum (no system under test runs).

Entries that need screen targets (the two pointer composites) take them from
the app's ``targets`` in ``suite_cells.json``; without them the trial is
reported as ``unmeasured`` and not run.

Standard library only; Python 3.10 compatible.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any

from harness.q2.action_path.executor import step_command
from harness.q2.vm import desktop
from harness.q2.vm.guest_http import GuestClient, GuestError
from harness.q2.vm.suite import guest_source

CTRL_D = {"op": "key", "keys": ["Control_L", "d"]}


def _guest(client: GuestClient, mode: str, config: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        out = client.run_script(guest_source("canary.py"), [mode, json.dumps(config)])
    except GuestError as exc:
        out = {"ok": False, "error": str(exc)[-800:]}
    out["_wall_s"] = round(time.monotonic() - started, 4)
    return out


def finish_actions(app: str, spec: dict[str, Any], expect: str) -> list[dict[str, Any]]:
    if app == "terminal":
        once = expect == "" or expect.endswith("\n")
        return [CTRL_D] if once else [CTRL_D, CTRL_D]
    return [{"op": "key", "keys": list(chord)} for chord in spec.get("finish_keys") or []]


def resolve_targets(entry: dict[str, Any], targets: dict[str, Any]) -> list[dict[str, Any]] | None:
    """The entry's IR actions with measured targets filled in; None if unmeasured."""
    if not entry.get("needs_targets"):
        return entry["actions"]
    measured = targets.get(entry["needs_targets"])
    if not measured:
        return None
    out = []
    for action in entry["actions"]:
        if action.get("op") == "click" and "target" in action:
            out.append(
                {
                    "op": "click",
                    "count": action.get("count", 1),
                    "x": measured["x"],
                    "y": measured["y"],
                }
            )
        elif action.get("op") == "drag" and "target" in action:
            out.append(
                {
                    "op": "drag",
                    "path": [measured["from"], measured["to"]],
                    "duration_ms": measured.get("duration_ms", 500),
                }
            )
        else:
            out.append(action)
    return out


CANARY_LIB = "/tmp/q2ap_canary_lib"


def install_canary_module(client: GuestClient) -> dict[str, Any]:
    """Write the frozen guest canary driver where the development measurement imports it."""
    script = (
        "import base64,os,sys\nos.makedirs(sys.argv[1],exist_ok=True)\n"
        "open(os.path.join(sys.argv[1],'canary.py'),'w').write(base64.b64decode(sys.argv[2]).decode())\n"
        "print('{\"ok\": true}')\n"
    )
    encoded = base64.b64encode(guest_source("canary.py").encode("utf-8")).decode("ascii")
    try:
        return client.run_script(script, [CANARY_LIB, encoded])
    except GuestError as exc:
        return {"ok": False, "error": str(exc)[-300:]}


def measure_targets(
    client: GuestClient, app: str, entry_id: str, trial: int, shot_dir: str | None
) -> dict[str, Any]:
    """Development only: the target from accessibility extents, and a screenshot for review."""
    out: dict[str, Any] = {}
    if app in ("writer", "chrome"):
        config = {"app": app, "entry": entry_id, "canary_dir": CANARY_LIB}
        try:
            out["extents"] = client.run_script(
                guest_source("canary_targets.py"), ["extents", json.dumps(config)]
            )
        except GuestError as exc:
            out["extents"] = {"ok": False, "error": str(exc)[-300:]}
    if shot_dir:
        path = f"/tmp/q2ap_canary_shot_{trial}.png"
        try:
            client.run_script(
                guest_source("canary_targets.py"), ["shot", json.dumps({"path": path})]
            )
            status, payload = client.read_file(path)
            if status == 200:
                name = f"{shot_dir}/canary-{trial:03d}-{app}-{entry_id}.png"
                with open(name, "wb") as handle:
                    handle.write(payload)
                out["screenshot"] = name
        except (GuestError, OSError) as exc:
            out["screenshot_error"] = str(exc)[-300:]
    return out


def canary_trial(
    client: GuestClient,
    canary: dict[str, Any],
    app: str,
    entry_id: str,
    trial: int,
    no_input: bool = False,
    measure: bool = False,
    shot_dir: str | None = None,
) -> dict[str, Any]:
    spec = canary["apps"][app]
    entry = canary["entries"][entry_id]
    started = time.monotonic()
    record: dict[str, Any] = {"app": app, "entry": entry_id, "trial": trial, "no_input": no_input}
    expect = entry["fixture_text"] if no_input else entry["expect"]
    actions = [] if no_input else resolve_targets(entry, spec.get("targets") or {})
    if actions is None and not measure:
        record["status"] = "unmeasured"
        return record
    config = {
        "app": app,
        "trial": trial,
        "fixture_text": entry["fixture_text"],
        "page": spec.get("page"),
        "flags": spec.get("flags"),
        "settings": spec.get("settings"),
    }
    record["prepare"] = prepared = _guest(client, "prepare", config)
    infra: list[str] = []
    if "argv" not in prepared:
        infra.append("prepare")
    else:
        status, text = client.launch(prepared["argv"])
        record["launch"] = {"status": status, "text": text[:200]}
        if status != 200:
            infra.append("launch")
    if not infra:
        record["wait"] = waited = _guest(
            client, "wait", {"app": app, "trial": trial, "timeout_s": 90}
        )
        if not waited.get("ok"):
            infra.append("app_not_ready")
    if measure and not infra and entry.get("needs_targets"):
        record["measured"] = measure_targets(client, app, entry_id, trial, shot_dir)
        target = ((record["measured"].get("extents") or {}).get("target")) or None
        if actions is None and target:
            actions = resolve_targets(entry, {entry["needs_targets"]: target})
    if actions is None:
        record["status"] = "unmeasured"
        actions = []
        infra.append("unmeasured")
    steps: list[dict[str, Any]] = []
    errors: list[str] = []
    if not infra and not no_input:
        for action in actions + finish_actions(app, spec, expect):
            step, _ = desktop.step(client, step_command(action), pause=0.0, a11y=False)
            result = ((step.get("execute") or {}).get("result")) or {}
            if result.get("returncode") not in (0, None):
                errors.append(
                    f"executor rc={result.get('returncode')}: {str(result.get('error'))[-300:]}"
                )
            infra += step.get("infra") or []
            steps.append({"op": action["op"], "timing_s": step["timing_s"], "infra": step["infra"]})
            if errors:
                break
        time.sleep(0.5)
    record["steps"] = steps
    if measure and shot_dir and (entry.get("needs_targets") or app == "chrome") and not no_input:
        after = measure_targets(client, "after", entry_id, trial, shot_dir)
        record.setdefault("measured", {})["after_screenshot"] = after.get("screenshot")
    readback = {"ok": False, "error": "not read"}
    if "argv" in prepared:
        readback = _guest(
            client,
            "readback",
            {
                "app": app,
                "trial": trial,
                "file": prepared.get("file"),
                "wait_cat_exit": not no_input,
            },
        )
    record["readback"] = readback
    if not readback.get("ok") and not infra:
        infra.append("readback")
    record["close"] = _guest(
        client, "close", {"app": app, "trial": trial, "file": prepared.get("file", "")}
    )
    text = readback.get("text")
    record["text"] = text
    record["expect"] = expect
    record["errors"] = errors
    record["infra"] = sorted(set(infra))
    record["pass"] = not infra and not errors and text == expect
    record["timing_s"] = round(time.monotonic() - started, 3)
    return record
