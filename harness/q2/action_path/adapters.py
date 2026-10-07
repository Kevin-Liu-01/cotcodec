"""Stage-1 harness adapters to the canonical IR (frozen in the executor addendum).

* **H-OSW-fixed**: ``upstream/osworld_bfd62bdc_fixed.py``, OSWorld ``bfd62bdc``'s
  ``parse_response`` with its emit boundary patched to IR and its own-spec bugs
  fixed (changes marked there). Coordinates are relative (0-999), scaled by
  the screenshot's size / 999 and clamped (``ir.clamp_point``).
* **H-GA**: ``upstream/gym_anything_aae6f7607.py``, gym-anything ``aae6f7607``'s
  ``_parse_response`` unmodified; its action dicts and metadata go through
  ``controls.translate_ga_dicts`` (gym-anything's step rule, key names and
  scroll convention), whose coordinates are clamped the same way.

``LAYERS`` maps every harness layer the suite runs, including the two C1
detection controls, to a function from one model response to IR dicts. A
response that yields invalid IR raises ``IRError``: the harness failed that
turn. Standard library only.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harness.q2.action_path import controls
from harness.q2.action_path.ir import SCREEN


def hosw_fixed(response: str) -> list[dict[str, Any]]:
    from harness.q2.action_path.upstream.osworld_bfd62bdc_fixed import Qwen35VLAgent

    _, actions = Qwen35VLAgent(coordinate_type="relative").parse_response(
        response,
        original_width=SCREEN[0],
        original_height=SCREEN[1],
        processed_width=SCREEN[0],
        processed_height=SCREEN[1],
    )
    return actions


def hga(response: str) -> list[dict[str, Any]]:
    from harness.q2.action_path.upstream.gym_anything_aae6f7607 import Qwen35VLAgent

    parsed = Qwen35VLAgent()._parse_response(response, SCREEN[0], SCREEN[1])
    return controls.translate_ga_dicts(parsed)


LAYERS: dict[str, Callable[[str], list[dict[str, Any]]]] = {
    "H-OSW-fixed": hosw_fixed,
    "H-GA": hga,
    "H-OSW-up": controls.run_hosw_up,
    "H-GA-buggy": controls.run_ga_buggy,
}


def turn_ir(layer: str, response: str) -> list[dict[str, Any]]:
    """The validated IR dicts of one turn for a harness layer (IRError on invalid IR)."""
    return [a.to_dict() for a in controls.to_ir(LAYERS[layer](response))]
