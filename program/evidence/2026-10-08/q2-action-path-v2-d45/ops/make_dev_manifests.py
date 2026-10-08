# ruff: noqa: E501
"""Write the D45 development manifests (seed 42, CPU only) and validate each.

Run from the repository root at c74eae0 (the commit the jobs run, exported read-only on the
host); it writes experiments/manifests/q2-action-path-v2/d45-*.yaml. Decision D45 narrows
D43's judge rule and changes verdict.py, a file every campaign executes, so the D43
development set (jobs 830-839, ``../q2-action-path-v2-d43/ops/make_dev_manifests.py``) is
repeated at this commit with the same workloads, Slurm resources and groups, under new
names and campaign ids.

Three groups (q2-action-path-v2 section 27):

* the targeted runs D43 asked for: L0-raw and L0-fixed on the four shell-grabbed chords, a
  sample of the ungrabbed chords and a sample of the gating set;
* the negative case: L0-fixed with the development fault that drops a chord's modifiers
  (``fault_drop_modifier``: ``omit`` and ``release_first``), on the four shell-grabbed and
  three ungrabbed chords;
* the final development runs repeated at this commit, because the judge (verdict.py), the
  guard and the lane changed: v1's jobs 703-708 (the guest-server fault injection, L0-fixed
  on one VM and on 8, H-OSW-fixed, H-GA and the canary), each with v1's workload unchanged.
"""

import copy
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, ".")
from harness.q2.vm import driver
from harness.q2.vm.manifest import runner_cpus, validate_manifest

SHA = "c74eae0aabb09fc5bc25e168758b529ede2a1410"
TREE = "4f66fe7edcce7133a178c720993c906dcb32aa470e02a05348ab07cad9fa8597"
PREREG_SHA = "b01f554f1409af8ff50a74ab54ad5bf31ea6029dea5b9b9dfa68f80a82af3f1e"
ROOT = "/home/kevin/cotcodec-runs/q2-action-path-v2/dev"
V1 = Path("experiments/manifests/q2-action-path")
OUT = Path("experiments/manifests/q2-action-path-v2")
cells = json.loads(Path("harness/q2/action_path/suite_cells.json").read_text())

GRABBED = ["chord_super_d", "chord_alt_f4", "chord_alt_tab", "chord_ctrl_alt_shift_r"]
UNGRABBED = ["chord_ctrl_c", "chord_shift_tab", "chord_ctrl_shift_t", "chord_ctrl_alone"]
GATING_SAMPLE = [
    "click_left_center",
    "drag_short",
    "scroll_down_3",
    "key_enter",
    "key_kp_enter",
    "caps_lock_roundtrip",
    "type_plain",
    "type_symbols_shifted",
    "type_unicode_bmp",
    "seq_type_chord_type",
]
SAMPLE = GRABBED + UNGRABBED + GATING_SAMPLE
NEGATIVE = GRABBED + UNGRABBED[:3]
H = "# q2-action-path-v2 development (seed 42, never evidence; decision D45), at c74eae0:\n"


def retarget(m, name, campaign):
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
    return m


def size(m):
    w = m["workload"]
    if w["kind"] != "canary-development" or "sessions" not in w:
        plan = driver.session_plan(m, cells)
        w["sessions"] = len(plan)
        w["trials"] = sum(len(s["trials"]) for s in plan)
    n = m["vm"]["concurrency"]
    cpus = runner_cpus(n) if n > 1 else m["runner"]["cpus"]
    m["runner"]["cpus"] = cpus
    per_vm = (
        600
        + w["sessions"] * (w["boot_timeout_s"] + w["settle_timeout_s"] + 240)
        + w["trials"] * w["max_trial_s"]
    )
    m["slurm"] = {
        "cpus": n * m["vm"]["cpu_cores"] + cpus,
        "memory_gb": max(12, n * (m["vm"]["memory_gb"] + 1) + 2),
        "minutes": max(m["slurm"]["minutes"], int(-(-per_vm // 600) * 10)),
    }


def write(m, stem, header):
    validate_manifest(m)
    (OUT / f"{stem}.yaml").write_text(header + yaml.safe_dump(m, sort_keys=False, width=100))
    w = m["workload"]
    print(
        stem,
        w["sessions"],
        "sessions",
        w["trials"],
        "trials",
        m["slurm"],
        m["vm"]["concurrency"],
        "VMs",
    )


def targeted(layer, stem, campaign, concurrency, session_trials, cell_ids, fault=None, reps=5):
    m = retarget(
        yaml.safe_load((V1 / "dev-l0-fixed-v14.yaml").read_text()), "q2ap-v2-d45", campaign
    )
    m["vm"]["concurrency"] = concurrency
    w = m["workload"]
    w.update(
        layer=layer,
        cells=cell_ids,
        reps=reps,
        settings=["screenshot", "screenshot+a11y"],
        session_trials=session_trials,
        max_trial_s=60,
    )
    if fault:
        w["fault_drop_modifier"] = fault
    size(m)
    return m


# 1. Targeted runs.
write(
    targeted("L0-raw", "d45-l0raw-sample-v1", "q2ap-v2-d45-l0raw-sample-v1", 1, 60, SAMPLE),
    "d45-l0raw-sample-v1",
    H
    + "# L0-raw (pyautogui, no interval or hold) on the four shell-grabbed chords, four ungrabbed\n"
    "# chords and ten gating entries, 5 repetitions per setting, one VM: the judge's reading of\n"
    "# events queued under a shell grab (D43, narrowed by D45), and C2's other entries\n"
    "# unchanged.\n",
)
write(
    targeted(
        "L0-fixed", "d45-l0fixed-sample-n8-v1", "q2ap-v2-d45-l0fixed-sample-n8-v1", 8, 10, SAMPLE
    ),
    "d45-l0fixed-sample-n8-v1",
    H + "# L0-fixed (10 ms between presses, 0.1 s hold) on the same 18 entries, 5 repetitions per\n"
    "# setting, 10 trials per session on 8 concurrent VMs.\n",
)
# 2. The negative case.
for fault in ("omit", "release_first"):
    stem = f"d45-drop-{fault.replace('_', '-')}-v1"
    write(
        targeted("L0-fixed", stem, f"q2ap-v2-{stem}", 1, 60, NEGATIVE, fault=fault),
        stem,
        H
        + f"# Negative case: L0-fixed with the development fault fault_drop_modifier={fault} (the\n"
        "# executor drops a chord's modifiers) on the four shell-grabbed and three ungrabbed chords,\n"
        "# 5 repetitions per setting, one VM. Every trial is expected to fail.\n",
    )
# 3. The final development runs, repeated (v1's 703-708 workloads unchanged).
for v1_file, stem, what in (
    (
        "dev-l0-restart-v3.yaml",
        "d45-l0-restart-v1",
        "the guest-server fault injection (as job 703)",
    ),
    ("dev-l0-fixed-v14.yaml", "d45-l0-fixed-v1", "L0-fixed, all 100 entries, one VM (as job 704)"),
    (
        "dev-l0-fixed-n8-v6.yaml",
        "d45-l0-fixed-n8-v1",
        "L0-fixed, all 100 entries, 8 VMs (as job 705)",
    ),
    ("dev-hosw-fixed-v10.yaml", "d45-hosw-fixed-v1", "H-OSW-fixed, every corpus cell (as job 706)"),
    ("dev-hga-v10.yaml", "d45-hga-v1", "H-GA, every corpus cell (as job 707)"),
    ("dev-canary-v12.yaml", "d45-canary-v1", "the canary, every app and entry (as job 708)"),
):
    m = retarget(yaml.safe_load((V1 / v1_file).read_text()), "q2ap-v2-d45-final", f"q2ap-v2-{stem}")
    check = copy.deepcopy(m)
    size(check)  # v1's workload and resources, unchanged: only the sizes are re-derived
    assert check["workload"] == m["workload"], stem
    write(
        m,
        stem,
        H + f"# Final development run repeated at this commit: {what}; v1's workload and\n"
        "# Slurm resources unchanged.\n",
    )
