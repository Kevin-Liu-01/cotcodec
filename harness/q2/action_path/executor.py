"""Host side of L0-fixed: one IR action -> one ``DesktopEnv.step`` command string.

The executor itself is ``harness/q2/vm/guest/l0_fixed.py`` (it runs in the
guest). Each IR action becomes one command: a short Python statement that
base64-decodes the executor's source with the action appended and executes it,
so the guest's ``python -c`` sees no quoting of user text at all (every typed
string travels inside the base64). ``device_action`` resolves the IR's keysym
names to keysym values, the form the guest code uses.

``terminate`` never becomes a command (it ends the cell). Standard library
only.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from harness.q2.action_path.ir import KEYSYM_VALUES, parse_action

L0_SOURCE_PATH = Path(__file__).resolve().parents[1] / "vm" / "guest" / "l0_fixed.py"


def l0_source() -> str:
    return L0_SOURCE_PATH.read_text(encoding="utf-8")


def device_action(raw: dict[str, Any]) -> dict[str, Any]:
    """The guest form of one IR action: keysym names become values; validated first."""
    action = parse_action(raw).to_dict()
    if action["op"] == "terminate":
        raise ValueError("terminate has no device action")
    out = {k: v for k, v in action.items() if k not in ("keys", "modifiers")}
    if "keys" in action:
        out["keysyms"] = [KEYSYM_VALUES[k] for k in action["keys"]]
    if "modifiers" in action:
        out["modifiers"] = [KEYSYM_VALUES[k] for k in action["modifiers"]]
    return out


def step_command(raw: dict[str, Any], source: str | None = None) -> str:
    """The ``DesktopEnv.step`` action string for one IR action (L0-fixed transport)."""
    payload = (source if source is not None else l0_source()) + (
        "\nrun_action(json.loads("
        + repr(json.dumps(device_action(raw), ensure_ascii=True))
        + "))\n"
    )
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return (
        "import base64 as _q2b; "
        f"exec(compile(_q2b.b64decode('{encoded}').decode('utf-8'), 'q2ap_l0', 'exec'), "
        "{'__name__': 'q2ap_l0'})"
    )
