"""Cost arithmetic for q2-stage1-rescoped-v1 (Stage S1a) from the frozen serving-probe-v2 card.

Read-only: imports the frozen budget module (harness/serving_probe/budget.py, SHA-256
cdb75646...) and reads job 466's point files and projection-v2.json. Prints JSON.
Usage: python cost_s1a.py <repo_root>
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import sys
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
sys.path.insert(0, str(REPO))
from harness.serving_probe import budget as B  # noqa: E402
from harness.serving_probe.prompts import modeled_prompt_tokens  # noqa: E402

EVID = REPO / "program/evidence/2026-10-07/serving-throughput-probe-v2"
points = {
    p.stem: json.loads(p.read_text()) for p in (EVID / "jobs/a-466/probe/points").glob("*.json")
}
proj = json.loads((EVID / "projection-v2.json").read_text())
ref = proj["q2"]["open_loop_reference"]
a1 = proj["q2"]["a1_noise"]
budget_sha = hashlib.sha256((REPO / "harness/serving_probe/budget.py").read_bytes()).hexdigest()
profiles = B.build_profiles(
    points,
    image_tokens=2040,
    unmeasured_multiplier=1.5,
    a11y_tokens=6144,
    thinking_output_tokens=2048,
)
out: dict = {
    "budget_py_sha256": budget_sha,
    "inputs": {"open_loop_reference": ref, "a1_min_rate": a1["min"]},
}

# 1. Reproduce the card's 9B cells (E = 360 episodes).
card = {}
for name, T in [
    ("h1-screenshot", 15),
    ("h1-a11y", 15),
    ("h2-thinking-screenshot", 100),
    ("h2-thinking-a11y", 100),
]:
    p = profiles[name]
    closed = B.closed_loop_gpu_hours(p, steps=T, episodes=360, t_env_s=2.5, gpus=1, multiplier=1.0)
    openl = B.open_loop_gpu_hours(
        steps=T,
        episodes=360,
        gpus=1,
        multiplier=1.0,
        requests_per_s=B.open_loop_cell_rate(ref, p, T),
    )
    card[name] = {
        "T": T,
        "V": p.vm_per_replica,
        "closed": round(closed, 4),
        "open": round(openl, 4),
        "per_episode": round(max(closed, openl) / 360, 6),
    }
out["card_cells_9b_per_360"] = card

# 2. The certified pair at T = 15 priced with the H2-thinking-screenshot profile.
T = 15
h2 = profiles["h2-thinking-screenshot"]
wave_s = sum(2.5 + h2.latency(t) for t in range(1, T + 1))
mean_prompt = h2.mean_prompt_tokens(T)
ratio = max(mean_prompt / ref["prompt_tokens"], 2048 / ref["output_tokens"])
r_cell = ref["rate"] / ratio
open_ep = T / r_cell / 3600
open_ep_high = T / (a1["min"] / ratio) / 3600
IDLE_S, TENV_HIGH = 180.0, 4.0


def per_episode(
    V: int, wave: float = wave_s, op: float = open_ep, oph: float = open_ep_high
) -> dict:
    closed = wave / V / 3600
    closed_high = (wave + IDLE_S + T * (TENV_HIGH - 2.5)) / V / 3600
    return {
        "V": V,
        "closed": round(closed, 6),
        "open": round(op, 6),
        "central": round(max(closed, op), 6),
        "closed_high": round(closed_high, 6),
        "open_high": round(oph, 6),
        "high": round(max(closed_high, oph), 6),
    }


out["h2_thinking_T15"] = {
    "sum_t_env_plus_L_s": round(wave_s, 2),
    "sum_L_r3_steps_1_15_s": round(sum(h2.measured[t] for t in range(1, T + 1)), 2),
    "thinking_penalty_s": round(h2.additive_s, 4),
    "mean_modelled_prompt_tokens": round(mean_prompt, 1),
    "open_loop_ratio": round(ratio, 4),
    "r_cell_req_s": round(r_cell, 4),
    "per_episode": {str(V): per_episode(V) for V in (8, 16, 20)},
    "t100_per_episode_card": card["h2-thinking-screenshot"]["per_episode"],
}

# 3. Sensitivity: both harnesses pass their thinking back and the template keeps it, so every
#    history entry carries up to 2,048 tokens instead of the profile's 300.
shape_tb = dataclasses.replace(h2.shape, response_tokens=2048)
mp_tb = sum(modeled_prompt_tokens(shape_tb, t) for t in range(1, T + 1)) / T
ratio_tb = max(mp_tb / ref["prompt_tokens"], 2048 / ref["output_tokens"])
open_tb = T / (ref["rate"] / ratio_tb) / 3600
scale = {
    t: max(1.0, modeled_prompt_tokens(shape_tb, t) / modeled_prompt_tokens(h2.shape, t))
    for t in range(1, T + 1)
}
wave_tb = sum(2.5 + h2.measured[t] * scale[t] + h2.additive_s for t in range(1, T + 1))
out["thinking_passback_bound"] = {
    "mean_modelled_prompt_tokens": round(mp_tb, 1),
    "max_prompt_step15": modeled_prompt_tokens(shape_tb, 15),
    "max_context_with_output": modeled_prompt_tokens(shape_tb, 15) + 2048,
    "open_loop_ratio": round(ratio_tb, 4),
    "open_binds_unchanged": ratio_tb == ratio,
    "closed_wave_s_latency_scaled_by_prompt_ratio": round(wave_tb, 1),
    "per_episode": {
        str(V): per_episode(V, wave_tb, open_tb, T / (a1["min"] / ratio_tb) / 3600)
        for V in (16, 20)
    },
    "note": "upper bound: scales the whole step latency (decode included) by the prompt ratio",
}

# 4. S1a plan and caps (D22 sum of caps).
LAUNCH_C, LAUNCH_H = 6 / 60, 10 / 60
hi16 = per_episode(16)["high"]
c20 = per_episode(20)["central"]


def a1_plan(K: int, V: int) -> dict:
    pe = per_episode(V)
    E = K * 2 * 2 * 2 * 2
    per_job_eps = K * 2 * 2
    return {
        "K_base": K,
        "V": V,
        "episodes": E,
        "central": round(E * pe["central"] + 4 * LAUNCH_C, 3),
        "high": round(E * pe["high"] + 4 * LAUNCH_H, 3),
        "per_job_high_min": round(per_job_eps * pe["high"] * 60 + 10, 1),
    }


plans = {
    "K32_V16": a1_plan(32, 16),
    "K32_V20": a1_plan(32, 20),
    "K36_V16": a1_plan(36, 16),
    "K16_V8": a1_plan(16, 8),
}
caps = {
    "O1_overlay": 3 / 60,
    "A0a_9b_pilot": 22 / 60,
    "A0b_anchor_smoke": 18 / 60,
    "O2_overlay": 3 / 60,
    "ANC_anchor": 32 / 60,
    "A1_4_jobs": 4 * 100 / 60,
}
caps["total"] = sum(caps.values())
out["s1a"] = {
    "a1_plans": plans,
    "caps_gpu_h": {k: round(v, 4) for k, v in caps.items()},
    "K_rule": "K_base <= 0.375 / c_proj (90 usable minutes per 100-minute job, 4K episodes/job)",
    "K_rule_at_card_high": round(0.375 / hi16, 2),
}
a0a_e = 16
out["s1a"]["A0a"] = {
    "episodes": a0a_e,
    "central": round(a0a_e * per_episode(16)["central"] + LAUNCH_C, 3),
    "high": round(a0a_e * hi16 + LAUNCH_H, 3),
}


def anchor_smoke() -> dict:
    """A0b: 4 dev episodes of OpenCUA-7B; one card-rule wave (H1 profile x1.5) plus a launch."""
    h1p = profiles["h1-screenshot"]
    w = sum(2.5 + 1.5 * h1p.latency(t) for t in range(1, T + 1)) / 3600
    return {"central": round(w + LAUNCH_C, 3), "high": round(w + LAUNCH_H, 3)}


# 5. OpenCUA-7B anchor: card H1-screenshot profile at the unmeasured-rung rule (x1.5), T = 15.
h1 = profiles["h1-screenshot"]
m = 1.5
wave_h1 = sum(2.5 + m * h1.latency(t) for t in range(1, T + 1))
r_h1 = B.open_loop_cell_rate(ref, h1, T)
anchor = {"wave_s": round(wave_h1, 1), "open_per_episode": round(T * m / r_h1 / 3600, 6)}
for V in (20, 32, 40):
    waves = math.ceil(116 / V)
    anchor[f"V{V}"] = {
        "card_closed_116": round(waves * wave_h1 / 3600, 4),
        "continuous_116": round(116 * wave_h1 / V / 3600, 4),
        "episodes_in_29_min_continuous": int(29 * 60 / wave_h1 * V),
    }
anchor["smoke_4_eps_central"] = round(wave_h1 / 3600 + LAUNCH_C, 3)
out["anchor"] = anchor


# 6. VM-hours (CPU-only lane): episode wall = GPU-h per episode x V; plus setup and checker.
def vm_h(E: int, V: int, setup_min: float, high: bool) -> float:
    pe = per_episode(V)
    return E * ((pe["high"] if high else pe["central"]) * V + setup_min / 60)


out["vm_hours"] = {
    "A1_K32_central": round(vm_h(512, 20, 1.5, False), 1),
    "A1_K32_high": round(vm_h(512, 16, 3, True), 1),
    "A1_reservation_bound_V20": round(4 * (100 / 60) * 20, 1),
    "A0a": round(16 * (per_episode(16)["high"] * 16 + 3 / 60), 1),
    "anchor_reservation_bound_V40": round(39 / 60 * 40, 1),
}


# 7. Stage S1b projections (card rule; unmeasured rung multipliers 1.5 and 4.5 until probe v3).
def rung_cost(E: int, mult: float) -> tuple[float, float]:
    return E * c20 * mult, E * hi16 * mult


ladder = {
    "9b_extra_2_sessions_60_tasks": rung_cost(60 * 2 * 2, 1.0),
    "4b_extra_2_sessions_60_tasks": rung_cost(240, 1.0),
    "35b_a3b_4_sessions_60_tasks": rung_cost(480, 1.5),
    "27b_4_sessions_60_tasks": rung_cost(480, 4.5),
}
lc = sum(v[0] for v in ladder.values()) + 16 * LAUNCH_C
lh = sum(v[1] for v in ladder.values()) + 16 * LAUNCH_H
a11y = profiles["h2-thinking-a11y"]
wave_a = sum(2.5 + a11y.latency(t) for t in range(1, T + 1))
ratio_a = max(a11y.mean_prompt_tokens(T) / ref["prompt_tokens"], 2048 / ref["output_tokens"])
open_a = T / (ref["rate"] / ratio_a) / 3600
pe_a_c = max(wave_a / 20 / 3600, open_a)
pe_a_h = max((wave_a + IDLE_S + T * 1.5) / 16 / 3600, T / (a1["min"] / ratio_a) / 3600)
obs_E = 60 * 2 * 2 * 4  # tasks x harness x observation x sessions, one rung
obs_c = obs_E / 2 * (c20 + pe_a_c) + 4 * LAUNCH_C
obs_h = obs_E / 2 * (hi16 + pe_a_h) + 4 * LAUNCH_H
out["s1b"] = {
    "ladder": {k: [round(v[0], 2), round(v[1], 2)] for k, v in ladder.items()},
    "ladder_total_central_high": [round(lc, 1), round(lh, 1)],
    "a11y_cell_per_episode_central_high": [round(pe_a_c, 6), round(pe_a_h, 6)],
    "observation_branch_one_rung_960_eps_central_high": [round(obs_c, 1), round(obs_h, 1)],
}

# 8. Pre-freeze review (2026-10-08): the slot also holds VM setup (central 90 s, high 180 s)
#    and OSWorld lib_run_single's 60 s settle after reset and 20 s before evaluation, which
#    S1a applies to both harnesses; the anchor's pinned runner adds 5 s after each step.
#    Caps follow the remainder rule (prereg section 6.1); the K-rule counts the USR1 lead,
#    the measured launch L and a 5% re-queue allowance.
SETUP_C, SETUP_H = 90.0, 180.0
SLEEPS = 60.0 + 20.0


def price_v2(V: int) -> dict:
    slot_c = wave_s + SETUP_C + SLEEPS
    slot_h = wave_s + SETUP_H + T * (TENV_HIGH - 2.5) + SLEEPS
    cc, ch = slot_c / V / 3600, slot_h / V / 3600
    return {
        "V": V,
        "slot_central_s": round(slot_c, 2),
        "slot_high_s": round(slot_h, 2),
        "closed_central": round(cc, 6),
        "closed_high": round(ch, 6),
        "central": round(max(cc, open_ep), 6),
        "high": round(max(ch, open_ep_high), 6),
    }


v2_prices = {str(V): price_v2(V) for V in (16, 20)}
anchor_slot_c = wave_h1 + 60 + 20 + T * 5.0 + SETUP_C
anchor_slot_h = wave_h1 + 60 + 20 + T * 5.0 + SETUP_H + T * (TENV_HIGH - 2.5)
CAPS2 = {"O1": 3, "A0a": 25, "A0b": 26, "O2": 3, "O2_retry": 3, "ANC": 52}


def a1_cap(anchor_runs: bool, a0b_runs: bool) -> int:
    used = CAPS2["O1"] + CAPS2["A0a"] + CAPS2["O2"] + CAPS2["O2_retry"]
    used += CAPS2["A0b"] if a0b_runs else 0
    used += CAPS2["ANC"] if anchor_runs else 0
    return math.floor((478 - used) / 4)


def k_rule(cap: int, L: float, c: float) -> dict:
    raw = ((cap - 3 - L) / 60) / (4 * 1.05 * c)
    return {"tasks_raw": round(raw, 2), "K_base": min(32, 8 * math.floor(raw / 8))}


branches = {
    "anchor_runs": (True, True),
    "anchor_unavailable_after_A0b": (False, True),
    "anchor_unavailable_before_A0b": (False, False),
}
cap_table = {}
for name, (runs, a0b) in branches.items():
    cap = a1_cap(runs, a0b)
    used = CAPS2["O1"] + CAPS2["A0a"] + CAPS2["O2"] + CAPS2["O2_retry"]
    used += (CAPS2["A0b"] if a0b else 0) + (CAPS2["ANC"] if runs else 0)
    cap_table[name] = {
        "A1_cap_min": cap,
        "total_min": used + 4 * cap,
        "total_gpu_h": round((used + 4 * cap) / 60, 4),
        "K_rule": {
            f"V{V}_L{L}_c{c}": k_rule(cap, L, max(v2_prices[str(V)]["high"], c))
            for V in (16, 20)
            for L in (3, 6)
            for c in (0.0, 0.0129, 0.0137)
        },
    }


def anchor_n(V: int, L: float, d: float, cap: int = 52) -> int:
    d = max(d, anchor_slot_c / 60)
    return min(116, V * math.floor((cap - 3 - L) / (1.25 * d)))


def plan_cost(K: int, V: int, cap: int) -> dict:
    pe = v2_prices[str(V)]
    E = K * 16
    return {
        "K": K,
        "V": V,
        "episodes": E,
        "central_gpu_h": round(E * pe["central"] + 4 * LAUNCH_C, 3),
        "high_gpu_h": round(E * pe["high"] + 4 * LAUNCH_H, 3),
        "per_job_high_min_incl_L6_usr1": round(4 * K * 1.05 * pe["high"] * 60 + 6 + 3, 1),
        "vm_h_central": round(E * pe["central"] * V, 1),
        "vm_h_high": round(E * pe["high"] * V, 1),
        "vm_h_reservation_bound": round(4 * (cap + 10) / 60 * V, 1),
    }


L_C, L_H = 3.0, 6.0  # launch to first request: job 466 took 2.4 min; 6 is the plan value


def jobs_v2(K: int, V: int, anchor_n: int) -> dict:
    """Central and high GPU-h per job (high A1 includes the 5% re-queue allowance)."""
    pe = v2_prices[str(V)]
    waves = math.ceil(anchor_n / 32) if anchor_n else 0
    rows = {
        "O1": (round(44 / 3600, 3), 0.05),
        "A0a": (
            round((L_C + v2_prices[str(V)]["slot_central_s"] / 60) / 60, 3),
            round((L_H + v2_prices[str(V)]["slot_high_s"] / 60) / 60, 3),
        ),
        "A0b": (
            round((L_C + anchor_slot_c / 60) / 60, 3),
            round((L_H + anchor_slot_h / 60) / 60, 3),
        ),
        "O2": (round(44 / 3600, 3), 0.05),
        "O2_retry": (0.0, 0.05),
        "ANC": (
            round((L_C + waves * anchor_slot_c / 60) / 60, 3) if waves else 0.0,
            round((L_H + waves * anchor_slot_h / 60) / 60, 3) if waves else 0.0,
        ),
        "A1": (
            round(K * 16 * pe["central"] + 4 * L_C / 60, 3),
            round(K * 16 * 1.05 * pe["high"] + 4 * L_H / 60, 3),
        ),
    }
    return {
        "K": K,
        "V": V,
        "anchor_tasks": anchor_n,
        "jobs_central_high": {k: list(v) for k, v in rows.items()},
        "total_central_high": [
            round(sum(v[0] for v in rows.values()), 3),
            round(sum(v[1] for v in rows.values()), 3),
        ],
    }


out["s1a_v2"] = {
    "jobs_v2": {
        "anchor_runs_K24_V20_n96": jobs_v2(24, 20, 96),
        "anchor_unavailable_K32_V20": jobs_v2(32, 20, 0),
    },
    "prices": v2_prices,
    "a0a_slot_high_min": round(v2_prices["20"]["slot_high_s"] / 60, 2),
    "anchor_slot_min": {
        "central": round(anchor_slot_c / 60, 2),
        "high": round(anchor_slot_h / 60, 2),
    },
    "a0_cap_need_min_L6": {
        "A0a": round(6 + 1.25 * v2_prices["20"]["slot_high_s"] / 60 + 3, 2),
        "A0b": round(6 + 1.25 * anchor_slot_h / 60 + 3, 2),
    },
    "caps": CAPS2,
    "remainder_rule": cap_table,
    "anchor_n_examples": {
        f"V{V}_L{L}_d{d}": anchor_n(V, L, d)
        for V in (16, 24, 32)
        for L in (4, 6)
        for d in (8.0, 10.0, 12.0, 13.17)
    },
    "plans": {
        "anchor_runs_K24_V20": plan_cost(24, 20, cap_table["anchor_runs"]["A1_cap_min"]),
        "anchor_runs_K32_V20": plan_cost(32, 20, cap_table["anchor_runs"]["A1_cap_min"]),
        "anchor_unavailable_K32_V20": plan_cost(
            32, 20, cap_table["anchor_unavailable_before_A0b"]["A1_cap_min"]
        ),
        "N16_K24_V16": plan_cost(24, 16, cap_table["anchor_unavailable_after_A0b"]["A1_cap_min"]),
    },
    "anchor_vm_h_reservation_bound_V32": round((CAPS2["ANC"] + 10) / 60 * 32, 1),
    "a1_c_a0a_for_K24_at_cap": {
        name: round(((row["A1_cap_min"] - 3 - 6) / 60) / (4 * 1.05 * 24) / 1.25 * 20 * 3600 / 60, 2)
        for name, row in cap_table.items()
    },
    "cpus": {
        "gpu_job": 32,
        "vm_job_V16": 4 * 16 + 8,
        "vm_job_V20": 4 * 20 + 10,
        "vm_job_V32": 4 * 32 + 16,
        "a1_V20_one_size": 32 + 90,
        "anc_V32": 32 + 144,
        "two_sizes_V20_concurrent": 2 * (32 + 90),
    },
}
sm = anchor_smoke()
anc_c = round(anchor["V40"]["continuous_116"] + LAUNCH_C, 3)
ov_c = round(44 / 3600, 3)  # job 464's measured overlay build, 44 s
rows = {
    "O1": (ov_c, 0.05),
    "A0a": (out["s1a"]["A0a"]["central"], out["s1a"]["A0a"]["high"]),
    "A0b": (sm["central"], sm["high"]),
    "O2": (ov_c, 0.05),
    "ANC": (anc_c, round(32 / 60, 3)),
    "A1_K32_V16": (plans["K32_V16"]["central"], plans["K32_V16"]["high"]),
}
out["s1a"]["jobs_central_high"] = {k: list(v) for k, v in rows.items()}
out["s1a"]["total_central_high"] = [
    round(sum(v[0] for v in rows.values()), 3),
    round(sum(v[1] for v in rows.values()), 3),
]
print(json.dumps(out, indent=1))
