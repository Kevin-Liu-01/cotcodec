# ruff: noqa: E501
"""Write the v2 development manifests (seed 42, decision D40) and validate each.

Run from the repository root at e66bf16 (the export the jobs ran); it writes
experiments/manifests/q2-action-path-v2/*.yaml from v1's last development manifest.
"""

import copy
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, ".")
from harness.q2.vm import driver
from harness.q2.vm.manifest import validate_manifest

SHA = "e66bf1665ee9484e9c95bc6f4509780311234da4"
TREE = "73e373a20c4a974e0ee81dce212360b3877df2abfa1c3b8cba8fbc50b0f0e4be"
PREREG_SHA = "81a809a1c2423770b7590e1777005043c74cca3a70ff23bd677e0520a5cb18ad"
ROOT = "/home/kevin/cotcodec-runs/q2-action-path-v2/dev"
OUT = Path("experiments/manifests/q2-action-path-v2")
template = yaml.safe_load(
    Path("experiments/manifests/q2-action-path/dev-l0-fixed-v14.yaml").read_text()
)
cells = json.loads(Path("harness/q2/action_path/suite_cells.json").read_text())
CHORDS = [
    "chord_ctrl_c",
    "chord_ctrl_a",
    "chord_ctrl_shift_t",
    "chord_ctrl_shift_arrow",
    "chord_shift_tab",
    "chord_alt_f4",
    "chord_super_d",
    "chord_ctrl_home",
    "chord_shift_arrow_left",
    "chord_ctrl_alt_shift_r",
    "chord_alt_tab",
    "chord_shift_alone",
    "chord_ctrl_alone",
]
EXPOSURE = [
    "chord_super_d",
    "chord_alt_f4",
    "chord_alt_tab",
    "chord_ctrl_alt_shift_r",
    "type_unicode_bmp",
    "type_emoji",
    "key_menu",
    "type_plain",
]


def make(name, campaign, layer, cell_ids, session_trials, concurrency, header):
    m = copy.deepcopy(template)
    m["name"], m["campaign_id"], m["experiment_id"] = name, campaign, "q2-action-path-v2"
    m["preregistration"] = {
        "path": "program/preregistrations/q2-action-path-v2.md",
        "status": "draft",
        "sha256": PREREG_SHA,
    }
    m["git_sha"] = SHA
    m["source"] = {"host_dir": f"{ROOT}/src/{SHA}", "tree_sha256": TREE}
    m["run_root"] = f"{ROOT}/runs"
    m["model"]["reason"] = "development runs of the action-path executor and controls load no model"
    m["vm"]["concurrency"] = concurrency
    runner_cpus = max(1, min(20, -(-concurrency // 2)))
    m["runner"]["cpus"] = runner_cpus
    w = m["workload"]
    w.update(
        layer=layer,
        cells=cell_ids,
        reps=5,
        settings=["screenshot", "screenshot+a11y"],
        session_trials=session_trials,
        max_trial_s=60,
    )
    plan = driver.session_plan(m, cells)
    w["sessions"] = len(plan)
    w["trials"] = sum(len(s["trials"]) for s in plan)
    budget = (
        600
        + w["sessions"] * (w["boot_timeout_s"] + w["settle_timeout_s"] + 240)
        + w["trials"] * w["max_trial_s"]
    )
    m["slurm"] = {
        "cpus": concurrency * m["vm"]["cpu_cores"] + runner_cpus,
        "memory_gb": max(12, concurrency * (m["vm"]["memory_gb"] + 1) + 2),
        "minutes": int(-(-budget // 600) * 10),
    }
    validate_manifest(m)
    text = header + yaml.safe_dump(m, sort_keys=False, width=100)
    (OUT / f"{campaign.removeprefix('q2ap-v2-')}.yaml").write_text(text)
    firsts = [s["trials"][0][1] for s in plan]
    print(
        campaign,
        w["sessions"],
        "sessions",
        w["trials"],
        "trials",
        m["slurm"],
        "first trials:",
        firsts,
    )


H = "# q2-action-path-v2 development (seed 42, never evidence; decision D40), at e66bf16:\n"
make(
    "q2ap-v2-dev-raw",
    "q2ap-v2-dev-l0raw-chords-v1",
    "L0-raw",
    CHORDS,
    60,
    1,
    H
    + "# L0-raw (pyautogui.hotkey, no interval or hold) on the 13 chord entries, 5 repetitions per\n"
    "# setting, one VM: reproduces v1's C2 failure of chord_super_d and compares the shell-grabbed\n"
    "# chords with the others.\n",
)
for campaign, st, n in (
    ("q2ap-v2-dev-l0fixed-superd-n8-v1", 10, 8),
    ("q2ap-v2-dev-l0fixed-superd-n16-v1", 5, 16),
    ("q2ap-v2-dev-l0fixed-superd-n8-v2", 8, 8),
):
    make(
        "q2ap-v2-dev-superd",
        campaign,
        "L0-fixed",
        EXPOSURE,
        st,
        n,
        H
        + f"# L0-fixed (10 ms between presses, 0.1 s hold, settle) on chord_super_d with the other shell\n"
        f"# chords and keymap-changing typing, 5 repetitions per setting, {st} trials per session on\n"
        f"# {n} concurrent VMs: is L0-fixed exposed when chord_super_d is not a session's first key?\n",
    )
