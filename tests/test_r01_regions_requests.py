"""R01 v2: the clock box, region composites, the request rebuilder and prompt-id fidelity."""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image, ImageDraw

from harness.q2_stage1 import agents
from harness.q2_stage1.engine import EngineClient
from harness.r01 import fake_engine, regions, requests


def frame(label: str, *, caret: bool = False, shade: int = 40, label_x: int = 930) -> bytes:
    image = Image.new("RGB", (1920, 1080), (shade, shade, shade))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 1919, 31], fill=(20, 20, 20))
    draw.text((label_x, 8), label, fill=(255, 255, 255))
    if caret:
        draw.rectangle([500, 500, 501, 520], fill=(0, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_clock_box_covers_the_full_label_not_only_the_changed_digits():
    a, b = frame("Oct 11 10:41"), frame("Oct 11 10:42")
    fit = regions.fit_clock_box([a, b])
    assert fit["ok"]
    box = regions.Box.of(fit["box"])
    # the hour digits did not change in the fitting pair, yet a later hour change stays inside
    later = frame("Oct 11 11:02")
    assert not regions.differs_outside(a, later, box)
    assert regions.differs_inside(a, later, box)
    assert fit["area_share"] < 0.02


def test_clock_box_stops_when_the_label_leaves_the_centre_segment():
    wide = frame("Oct 11 10:41", label_x=630)  # starts left of the centre third (640 px)
    fit = regions.fit_clock_box([wide])
    assert not fit["ok"] and "edge" in fit["reason"]


def test_composites_separate_clock_and_non_clock_regions():
    a, b = frame("Oct 11 10:41"), frame("Oct 11 10:44", caret=True)
    box = regions.Box.of(regions.fit_clock_box([a, b])["box"])
    comp = requests.composites(a, b, box)
    assert regions.differs_inside(comp["R"], comp["C"], box)
    assert not regions.differs_outside(comp["R"], comp["C"], box)
    assert regions.differs_outside(comp["R"], comp["O"], box)
    assert not regions.differs_inside(comp["R"], comp["O"], box)
    assert comp["X"] == b
    checks = requests.check_composites(a, b, box)
    assert all(checks.values())
    # deterministic bytes
    assert regions.swap_box(a, b, box) == regions.swap_box(a, b, box)


def test_mask_and_census_classify_caret_and_clock():
    a, b = frame("Oct 11 10:41"), frame("Oct 11 10:44", caret=True)
    box = regions.Box.of(regions.fit_clock_box([a, b])["box"])
    census = regions.census(a, b, box)
    assert census["clock"] >= 1 and census["caret_like"] == 1 and census["other"] == 0
    assert census["outside_box"]
    masked_a = regions.mask_box(a, box, [20, 20, 20])
    masked_c = regions.mask_box(regions.swap_box(a, b, box), box, [20, 20, 20])
    assert masked_a == masked_c


def test_a_pair_without_a_clock_change_is_flagged():
    a = frame("Oct 11 10:41")
    b = frame("Oct 11 10:41", caret=True)
    box = regions.Box.of(regions.fit_clock_box([a, b])["box"])
    checks = requests.check_composites(a, b, box)
    assert not checks["clock_differs"] and checks["nonclock_differs"]


def test_step1_rebuild_is_the_frozen_clients_request():
    png = frame("Oct 11 10:41")
    built = requests.rebuild("Open the file.", [png], [])
    shot = agents.process_image(png)
    from datetime import datetime

    messages = agents.build_messages(
        system=agents.osw_system_prompt(datetime(2026, 10, 8)),
        instruction="Open the file.",
        screenshots=[shot.b64],
        responses=[],
        previous=[],
    )
    body = EngineClient("/x", "s1a-model").body(messages, requests.SAMPLING)
    body.update(requests.LOGPROB_FIELDS)
    assert built["body"] == body
    assert built["body_sha256"] == requests.body_sha256(body)
    assert built["date_line"] == "Thursday, October 08, 2026"
    assert requests.without_logprobs(built["body"]) == EngineClient("/x", "s1a-model").body(
        messages, requests.SAMPLING
    )


def test_step2_rebuild_passes_the_recorded_reply_back():
    reply = (
        "<think>\nlook\n</think>\n\nAction: click.\n<tool_call>\n<function=computer_use>\n"
        "<parameter=action>\nleft_click\n</parameter>\n"
        "<parameter=coordinate>\n[10, 20]\n</parameter>\n"
        "</function>\n</tool_call>"
    )
    built = requests.rebuild(
        "Open the file.", [frame("Oct 11 10:41"), frame("Oct 11 10:41", shade=60)], [reply]
    )
    roles = [m["role"] for m in built["body"]["messages"]]
    assert roles == ["system", "user", "assistant", "user"]
    assert built["body"]["messages"][2]["content"][0]["text"] == reply
    with pytest.raises(ValueError):
        requests.rebuild("x", [frame("a")], ["extra"])


def test_every_variant_keeps_the_reference_prompt_ids():
    a, b = frame("Oct 11 10:41"), frame("Oct 11 10:44", caret=True)
    box = regions.Box.of(regions.fit_clock_box([a, b])["box"])
    reqs = requests.pair_requests(
        "Do it.",
        a,
        b,
        box,
        reply1="Action: wait.",
        a_step2=frame("x", shade=70),
        b_step2=frame("y", shade=71),
    )
    ids = {k: fake_engine.prompt_ids(v["body"]["messages"]) for k, v in reqs.items()}
    assert ids["R"] == ids["C"] == ids["O"] == ids["X"]
    assert ids["R2"] == ids["C2"] == ids["O2"] == ids["X2"] != ids["R"]
    assert len({v["body_sha256"] for k, v in reqs.items() if k in requests.CELLS_STEP1}) == 4


def test_fidelity_rule_stops_above_ten_percent():
    recorded = {f"r{i}": f"d{i}" for i in range(20)}
    observed = dict(recorded)
    observed["r0"] = "bad"
    observed["r1"] = None
    ok = requests.fidelity(observed, recorded)
    assert ok["failing"] == ["r0", "r1"] and not ok["stop"]
    observed["r2"] = "bad"
    assert requests.fidelity(observed, recorded)["stop"]


def test_episode_choice_is_seeded_and_skips_ineligible_episodes():
    cands = [
        {"session": "S1", "rerun": 1, "steps": 1, "step1_ir": [{"op": "click"}]},
        {
            "session": "S1",
            "rerun": 2,
            "steps": 5,
            "step1_ir": [{"op": "terminate", "status": "success"}],
        },
        {"session": "S2", "rerun": 1, "steps": 5, "step1_ir": [{"op": "click"}]},
        {"session": "S2", "rerun": 2, "steps": 4, "step1_ir": [{"op": "type"}]},
    ]
    first = requests.choose_episode("t", cands)
    assert first in cands[2:]
    assert requests.choose_episode("t", list(reversed(cands))) == first
    with pytest.raises(ValueError):
        requests.choose_episode("t", cands[:2])
    json.dumps(first)
