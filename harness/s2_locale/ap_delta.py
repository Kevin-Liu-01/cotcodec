"""S2 v4 P0.6 (K1): the registered deviation of ``q2-action-path-v2`` on the five cell images.

Registration ``s2-arabic-cua-locale-v4``, section "K1". The suite (executor, catalog, corpus,
verdict code, trial orders, sessions, infrastructure rule, pass lines) is ``q2-action-path-v2``'s,
run by its own code: ``harness/q2/`` is not edited, and every campaign manifest is admitted by
``harness.q2.vm.manifest.validate_manifest`` with the ledger, whose closed-world rule requires
every file under ``harness/q2`` to be the file the frozen executor addendum pins. The deviation
is the disk: each campaign's ``vm.qcow2`` names a cell image (host path, SHA-256 and size from
``harness/s2_locale/images.json``) instead of the certified ``Ubuntu.qcow2``; its provenance fields
(``source_url``, ``revision``, ``archive_sha256``, ``license``), which harness/q2's validator
requires to be a revision-pinned Hugging Face URL, name the certified disk the image is derived
from (``CERTIFIED_PROVENANCE``), and the image itself is identified by its pin and its build
record. This module renders those manifests, checks them, and drives harness/q2 in one Slurm job
(``infra/slurm/host-single-node/s2v4-apdelta.sbatch``):

* Single-image checks (C1, C2, C3, A1, A2, A3, A5, A6): an ``ap_delta`` manifest lists q2
  campaign manifests for one check on one image (C3: all 47 mutant and reference runs). The job
  runs them one after another, each through ``python3 -m harness.q2.vm.driver`` unchanged (one VM
  at a time, as section 7 requires), each into its own run directory in harness/q2's layout
  (``manifest.json``, ``preflight.txt`` with the batch's ``driver_exit=... labelled_containers_
  left=...`` line, ``receipt.json``, ``cycles/``), so ``acceptance.load`` reads them as it read
  attempt 1's.
* The V = 20 rung (``rung``): harness/q2's validator admits rungs at N = 8, 16, 24, 32 and 40
  only, and one disk per manifest. The rung manifest is q2's ladder manifest at N = 20 with
  ``manifest.ladder_reps(20)`` = 12 repetitions of the seed-43 order (2,400 trials in 40
  sessions) and ``manifest.runner_cpus(20)`` = 10 runner CPUs. It is checked by q2's validator
  as a shadow at N = 24 (every other field, the ledger and the closed world), and its N = 20
  fields against q2's own functions. ``run_rung`` is driver.main's concurrent branch with one
  change: 20 workers on the slices of ``driver.plan_cpusets_multi``, worker k on image
  ``RUNG_CELLS[k % 5]``, worker k running sessions k and k + 20 of ``driver.acceptance_plan``,
  so session i runs on image i mod 5 (8 sessions per image, four VMs per image at once), each
  through the unchanged ``driver.run_cycle`` with that image's ``vm.qcow2``. Before any session it
  makes ``driver.main``'s pre-run checks with harness/q2's own functions (Docker's server facts,
  the VM image's ID and digest reference agreeing, the runner image present, per image the
  regular read-only file, its size and digest and ``qemu-img info``, and the dangling volumes
  before and after); every image is hashed before and after; the receipt has harness/q2's
  fields, so ``acceptance.rung`` reads it.

Purposes: ``development`` (q2 development workloads, seed 42, on cell images) before the freeze;
``k1`` (the registered campaigns, ``K1_PLAN``) only after it, from an export of the freeze commit
(``vm_lane.frozen_registration`` and ``vm_lane.check_export``, the lane's own gate). Standard
library only on the host; ``render`` runs on the Mac (it uses
``scripts/render_q2_action_path_manifest.py``, which needs PyYAML).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.s2_locale import vm_lane as L

SCHEMA = "s2v4-apdelta-v1"
EXPERIMENT_ID = L.EXPERIMENT_ID
PURPOSES = ("development", "k1")
CHECKS = ("C1", "C2", "C3", "A1", "A2", "A3", "A5", "A6", "rung")
K1_CELLS = ("E", "A", "ER", "AR", "PL")
RUNG_CELLS = K1_CELLS
RUNG_N = 20
RUNG_SHADOW_N = 24  # an admissible rung of q2's validator, for every field but the N = 20 ones
K1_PLAN = "experiments/manifests/s2v4/k1-plan.json"
K1_PLAN_SHA256 = "e1a4ac5b51d22a95f04905b0ebb7018ab521e2b21ca2abe2d62ced4dfd1a83cf"
RUN_ROOT = L.RUN_ROOT
K1_ROOT = f"{RUN_ROOT}stage0/s2v4/k1"
BATCH = "infra/slurm/host-single-node/s2v4-apdelta.sbatch"
CERTIFIED_PROVENANCE = {
    "source_url": "https://huggingface.co/datasets/xlangai/ubuntu_osworld/resolve/"
    "a5d9c3eaae98eebf6e3a0beb84e7e47cf72ae133/Ubuntu.qcow2.zip",
    "archive_sha256": "b795b6cd4c69b252c1b4f10150a347795555032501b60fd031751ed09b896712",
    "revision": "a5d9c3eaae98eebf6e3a0beb84e7e47cf72ae133",
    "license": "apache-2.0",
}
CELLS_FILE = "harness/q2/action_path/suite_cells.json"
VOLUME_PLAN = "harness/q2/action_path/volume_plan.json"
SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")


class DeltaError(ValueError):
    """The manifest is outside the registration; nothing may start."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DeltaError(message)


# --------------------------------------------------------------------------- keys and plan


def campaign_key(q2m: Mapping[str, Any]) -> dict[str, Any]:
    """What identifies a q2 campaign in the K1 plan."""
    w = q2m.get("workload") or {}
    seeds = (q2m.get("randomness") or {}).get("seeds") or []
    return {"kind": w.get("kind"), "criterion": w.get("criterion"), "layer": w.get("layer"),
            "seed": seeds[0] if seeds else None, "mutant": w.get("mutant"),
            "concurrency": (q2m.get("vm") or {}).get("concurrency")}  # fmt: skip


def k1_plan_entries(operators: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The registered K1 campaigns (section "K1"), per check and cell, as campaign keys.
    ``operators``: ``mutation_operators.yaml`` (C3's scored mutant and layer pairs)."""
    def suite(criterion: str, layer: str, seed: int, mutant: str | None = None,
              concurrency: int = 1) -> dict[str, Any]:  # fmt: skip
        return {"kind": "suite-acceptance", "criterion": criterion, "layer": layer, "seed": seed,
                "mutant": mutant, "concurrency": concurrency}  # fmt: skip

    c3 = []
    for op in operators["operators"]:
        for layer, rule in sorted((op.get("applies") or {}).items()):
            if rule.get("status") == "scored":
                c3.append(suite("C3", layer, 42, op["id"]))
    c3 += [suite("C3", layer, 42, "none") for layer in ("L0-fixed", "H-OSW-fixed", "H-GA")]
    per_cell = {
        "C1": [suite("C1", "H-GA-buggy", 42), suite("C1", "H-OSW-up", 42)],
        "C2": [suite("C2", "L0-raw", 45)],
        "C3": c3,
        "A1": [suite("A1", "L0-fixed", 43), suite("A1", "L0-fixed", 44)],
        "A2": [suite("A2", "H-OSW-fixed", 43), suite("A2", "H-GA", 43)],
        "A5": [{"kind": "boot-reset-validation", "criterion": None, "layer": None, "seed": None,
                "mutant": None, "concurrency": 1}],
        "A6": [{"kind": "canary-acceptance", "criterion": None, "layer": None, "seed": 43,
                "mutant": None, "concurrency": 1}],
    }  # fmt: skip
    out = [{"check": check, "cell": cell, **key}
           for cell in K1_CELLS for check, keys in per_cell.items() for key in keys]
    out += [{"check": "A3", "cell": "AR", **suite("A3", layer, 43)}
            for layer in ("L0-fixed", "H-OSW-fixed", "H-GA")]
    out.append({"check": "rung", "cell": "+".join(RUNG_CELLS),
                **suite("ladder", "L0-fixed", 43, None, RUNG_N)})
    return out


def load_k1_plan(source_dir: Path) -> list[dict[str, Any]]:
    data = (source_dir / K1_PLAN).read_bytes()
    _require(hashlib.sha256(data).hexdigest() == K1_PLAN_SHA256,
             f"{K1_PLAN} is not the pinned K1 plan (K1_PLAN_SHA256)")  # fmt: skip
    return json.loads(data)["campaigns"]


# --------------------------------------------------------------------------- validation


def check_image_entry(q2m: Mapping[str, Any], cell: str, pins: Mapping[str, Any]) -> None:
    qcow2 = (q2m.get("vm") or {}).get("qcow2") or {}
    _require(cell in K1_CELLS and cell in pins, f"{cell}: not a K1 cell image")
    _require(qcow2.get("sha256") == pins[cell]["sha256"]
             and qcow2.get("size_bytes") == pins[cell]["size_bytes"],
             f"{cell}: vm.qcow2 is not the pinned cell image")  # fmt: skip
    path = str(qcow2.get("host_path", ""))
    _require(path.startswith(RUN_ROOT) and path.endswith(".qcow2") and ".." not in path,
             f"{cell}: vm.qcow2.host_path")  # fmt: skip
    for key, value in CERTIFIED_PROVENANCE.items():
        _require(qcow2.get(key) == value,
                 f"{cell}: vm.qcow2.{key} must name the certified disk the image derives from")


def q2_validate(q2m: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    """harness/q2's own admission: the validator, with the ledger for a scored campaign."""
    from harness.q2.vm.manifest import (
        ManifestError,
        ledger_paths,
        ledger_view,
        validate_manifest,
    )

    raw = json.loads(json.dumps(q2m))
    try:
        ledger = (ledger_view(str(source_dir), ledger_paths(raw))
                  if raw.get("purpose") == "acceptance" else None)  # fmt: skip
        return validate_manifest(raw, ledger)
    except ManifestError as exc:
        raise DeltaError(f"harness/q2 refuses the campaign {raw.get('campaign_id')}: {exc}") \
            from exc


def plan_counts(q2m: Mapping[str, Any], source_dir: Path) -> tuple[int, int]:
    """Sessions and trials of a suite-acceptance campaign (``driver.acceptance_plan``)."""
    from harness.q2.vm import driver

    cells = json.loads((source_dir / CELLS_FILE).read_text(encoding="utf-8"))
    volume = json.loads((source_dir / VOLUME_PLAN).read_text(encoding="utf-8"))
    plan = driver.acceptance_plan(json.loads(json.dumps(q2m)), cells, volume)
    return len(plan), sum(len(s["trials"]) for s in plan)


def check_rung(q2m: Mapping[str, Any], source_dir: Path, purpose: str) -> None:
    """The rung at N = 20: every field but the N = 20 ones through q2's validator (a shadow at
    N = 24), the N = 20 ones from q2's own functions."""
    from harness.q2.vm.manifest import ladder_reps, runner_cpus

    if purpose == "development":
        q2_validate(q2m, source_dir)  # development workloads may run N VMs (seed 42 only)
        return
    w = q2m["workload"]
    _require(q2m["vm"]["concurrency"] == RUNG_N, f"the rung runs N = {RUNG_N}")
    _require(w.get("criterion") == "ladder" and w.get("reps") == ladder_reps(RUNG_N),
             f"the rung repeats the seed-43 order {ladder_reps(RUNG_N)} times")  # fmt: skip
    _require(q2m["runner"]["cpus"] == runner_cpus(RUNG_N),
             f"the rung's runners share {runner_cpus(RUNG_N)} CPUs (section 9)")  # fmt: skip
    _require((w["sessions"], w["trials"]) == plan_counts(q2m, source_dir),
             "the rung's sessions and trials are not driver.acceptance_plan's")  # fmt: skip
    shadow = copy.deepcopy(dict(q2m))
    shadow["vm"]["concurrency"] = RUNG_SHADOW_N
    shadow["workload"]["reps"] = ladder_reps(RUNG_SHADOW_N)
    shadow["runner"]["cpus"] = runner_cpus(RUNG_SHADOW_N)
    shadow["workload"]["sessions"], shadow["workload"]["trials"] = plan_counts(shadow, source_dir)
    shadow["slurm"] = {"cpus": RUNG_SHADOW_N * shadow["vm"]["cpu_cores"] + runner_cpus(
        RUNG_SHADOW_N), "memory_gb": RUNG_SHADOW_N * (shadow["vm"]["memory_gb"] + 1) + 2,
        "minutes": 1440}  # fmt: skip
    q2_validate(shadow, source_dir)


def campaign_minutes(q2m: Mapping[str, Any], image_bytes: int) -> int:
    """The campaign's own Slurm minutes (harness/q2's worst-case budget, in the manifest) plus
    the image check the driver makes twice (before and after) at ``HASH_GB_PER_MIN``."""
    return int(q2m["slurm"]["minutes"]) + 2 * math.ceil(image_bytes / 1e9 / L.HASH_GB_PER_MIN)


def validate_manifest(raw: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    m = json.loads(json.dumps(raw))
    _require(m.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    _require(m.get("experiment_id") == EXPERIMENT_ID, f"experiment_id must be {EXPERIMENT_ID}")
    purpose = m.get("purpose")
    _require(purpose in PURPOSES, f"purpose must be one of {PURPOSES}")
    try:
        row = L.ledger_row(source_dir)
        if purpose == "development":
            _require(row is None, f"{EXPERIMENT_ID} is frozen: development no longer runs (D56)")
        else:
            _require(row is not None, f"k1 runs only after the freeze (no ledger row for "
                                      f"{EXPERIMENT_ID})")  # fmt: skip
            L.check_export(m, source_dir, L.frozen_registration(source_dir))
    except L.LaneError as exc:
        raise DeltaError(str(exc)) from exc
    _require(isinstance(m.get("name"), str) and bool(SAFE.fullmatch(m["name"])), "unsafe name")
    check = m.get("check")
    _require(check in CHECKS, f"check must be one of {CHECKS}")
    _require(str(m.get("run_root", "")).startswith(RUN_ROOT), "run_root outside the run root")
    pins = L.load_pins(source_dir)
    campaigns = m.get("campaigns") or []
    _require(bool(campaigns), "no campaigns")
    sha_file = source_dir / ".git_sha"
    export_sha = sha_file.read_text(encoding="utf-8").strip() if sha_file.is_file() else None
    seen: set[str] = set()
    for item in campaigns:
        q2m = item.get("manifest") or {}
        cid = str(q2m.get("campaign_id"))
        _require(cid not in seen, f"campaign {cid} twice")
        seen.add(cid)
        cells = item.get("cells") or []
        _require(bool(cells) and all(c in K1_CELLS for c in cells), f"{cid}: cells")
        multi = is_rung(item)
        if purpose == "k1":
            _require(multi == (check == "rung"), f"{cid}: only the rung check runs a rung")
        if multi:
            _require(purpose == "development" or len(campaigns) == 1,
                     "a rung manifest runs one campaign")  # fmt: skip
            _require(purpose == "development" or tuple(cells) == RUNG_CELLS,
                     f"the rung interleaves the five images {RUNG_CELLS}")  # fmt: skip
            _require(set(item.get("qcow2") or {}) == set(cells), f"{cid}: qcow2 per cell")
            for cell in cells:
                check_image_entry(dict(q2m, vm=dict(q2m["vm"], qcow2=item["qcow2"][cell])), cell,
                                  pins)  # fmt: skip
            check_image_entry(q2m, cells[0], pins)
            check_rung(q2m, source_dir, purpose)
        else:
            _require(len(cells) == 1, f"{cid}: a single-image campaign names one cell")
            check_image_entry(q2m, cells[0], pins)
            q2_validate(q2m, source_dir)
            _require(q2m["vm"]["concurrency"] == 1, f"{cid}: one VM at a time (section 7)")
        if export_sha is not None or purpose == "k1":
            _require(q2m.get("git_sha") == export_sha,
                     f"{cid}: git_sha is not the export's .git_sha")  # fmt: skip
    if purpose == "k1":
        check_registered(m, source_dir)
    return m


def is_rung(item: Mapping[str, Any]) -> bool:
    """A multi-image item (the rung, or a development rung): one disk per worker."""
    return len(item.get("cells") or []) > 1 or "qcow2" in item


def _canon(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted(json.dumps(dict(r), sort_keys=True) for r in rows)


def check_registered(m: Mapping[str, Any], source_dir: Path) -> None:
    """A k1 manifest runs the plan's campaigns for its check and cell: all of them, or, as one
    numbered part of a check too long for one job (``part``: index and count; C3 and A3), a
    subset in the plan's order, so the parts together run each campaign once."""
    plan = load_k1_plan(source_dir)
    cells = "+".join(m["campaigns"][0]["cells"])
    for item in m["campaigns"]:
        _require("+".join(item["cells"]) == cells,
                 f"every campaign of a k1 job runs on {cells}, the first campaign's image")
        _require(item["manifest"]["vm"]["qcow2"]["host_path"]
                 == m["campaigns"][0]["manifest"]["vm"]["qcow2"]["host_path"],
                 "every campaign of a k1 job mounts the first campaign's image")  # fmt: skip
    want = [{k: v for k, v in e.items() if k not in ("check", "cell")} for e in plan
            if e["check"] == m["check"] and e["cell"] == cells]
    got = [campaign_key(item["manifest"]) for item in m["campaigns"]]
    _require(bool(want), f"the K1 plan has no {m['check']} campaigns on {cells}")
    part = m.get("part")
    if part is None:
        _require(_canon(got) == _canon(want),
                 f"{m['check']} on {cells}: the campaigns are not the K1 plan's")  # fmt: skip
    else:
        _require(isinstance(part, dict) and 1 <= int(part.get("index", 0)) <= int(
            part.get("of", 0)), "part: index of count")  # fmt: skip
        keys = [json.dumps(dict(w), sort_keys=True) for w in want]
        mine = [json.dumps(dict(g), sort_keys=True) for g in got]
        _require(len(set(mine)) == len(mine) and set(mine) <= set(keys),
                 f"{m['check']} on {cells}: a part runs distinct campaigns of the K1 plan")
        positions = [keys.index(k) for k in mine]
        _require(positions == sorted(positions), "a part keeps the plan's order")
    for item in m["campaigns"]:
        q2m = item["manifest"]
        _require(q2m.get("purpose") in ("acceptance", "infrastructure-validation"),
                 "a K1 campaign is a scored campaign")  # fmt: skip
        _require(str(q2m.get("run_root", "")).startswith(K1_ROOT),
                 f"a K1 campaign runs under {K1_ROOT}")  # fmt: skip


def image_bytes(m: Mapping[str, Any]) -> int:
    sizes = {}
    for item in m["campaigns"]:
        entries = item.get("qcow2") or {item["cells"][0]: item["manifest"]["vm"]["qcow2"]}
        for e in entries.values():
            sizes[e["host_path"]] = e["size_bytes"]
    return sum(sizes.values())


def check_slurm(m: Mapping[str, Any]) -> dict[str, int]:
    slurm = m.get("slurm") or {}
    cpus, memory, minutes = slurm.get("cpus"), slurm.get("memory_gb"), slurm.get("minutes")
    need_cpus = max(int(item["manifest"]["slurm"]["cpus"]) for item in m["campaigns"])
    need_mem = max(int(item["manifest"]["slurm"]["memory_gb"]) for item in m["campaigns"])
    for item in m["campaigns"]:
        if is_rung(item):
            q2m = item["manifest"]
            n, cores = q2m["vm"]["concurrency"], q2m["vm"]["cpu_cores"]
            need_cpus = max(need_cpus, n * cores + q2m["runner"]["cpus"])
            need_mem = max(need_mem, n * (q2m["vm"]["memory_gb"] + 1) + 2)
    total = 10 + sum(campaign_minutes(item["manifest"], image_bytes(
        {"campaigns": [item]})) for item in m["campaigns"])  # fmt: skip
    _require(isinstance(cpus, int) and need_cpus <= cpus <= 160, f"slurm.cpus {need_cpus}-160")
    _require(isinstance(memory, int) and memory >= need_mem, f"slurm.memory_gb >= {need_mem}")
    _require(isinstance(minutes, int) and total <= minutes <= 1440,
             f"slurm.minutes must cover every campaign and its image checks ({total})")
    return {"cpus": cpus, "memory_gb": memory, "minutes": minutes, "budget_minutes": total}


# --------------------------------------------------------------------------- run


def docker(*args: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout,
                          check=False)  # fmt: skip


def labelled_left(job_id: str) -> int:
    out = docker("ps", "-aq", "--filter", f"label=cotcodec.slurm_job={job_id}").stdout.split()
    return len(out)


def write_preflight(run_dir: Path, job_id: str, extra: Mapping[str, Any]) -> None:
    lines = [f"job_id={job_id}"] + [f"{k}={v}" for k, v in extra.items()]
    (run_dir / "preflight.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_campaign(q2m: Mapping[str, Any], run_dir: Path, source_dir: Path, job_id: str,
                 timeout_s: float, stop: list[bool]) -> int:  # fmt: skip
    """One single-image campaign through harness/q2's driver, unchanged, as vm-campaign.sbatch
    runs it; the batch's end line is appended to its ``preflight.txt``."""
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(q2m, indent=2, sort_keys=True))
    from harness.q2.vm.manifest import manifest_sha256

    write_preflight(run_dir, job_id, {"manifest_sha256": manifest_sha256(dict(q2m)),
                                      "ap_delta": "1"})  # fmt: skip
    argv = [sys.executable, "-E", "-s", "-m", "harness.q2.vm.driver", "--manifest",
            str(run_dir / "manifest.json"), "--run-dir", str(run_dir), "--source-dir",
            str(source_dir), "--job-id", job_id]  # fmt: skip
    proc = subprocess.Popen(argv, cwd=source_dir)
    try:
        rc = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGTERM)
        rc = proc.wait(timeout=120)
    if stop and stop[0] and rc == 0:
        rc = 143
    ids = docker("ps", "-aq", "--filter", f"label=cotcodec.slurm_job={job_id}").stdout.split()
    if ids:
        docker("rm", "--force", "--volumes", *ids, timeout=120)
    with (run_dir / "preflight.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"driver_exit={rc} labelled_containers_left={labelled_left(job_id)}\n")
    return rc


def run_rung(item: Mapping[str, Any], run_dir: Path, source_dir: Path, job_id: str) -> int:
    """The N = 20 rung over the five images (driver.main's concurrent branch, per-worker disk)."""
    from concurrent.futures import ThreadPoolExecutor

    from harness.q2.vm import driver
    from harness.q2.vm.manifest import manifest_sha256

    q2m = dict(item["manifest"])
    cells = list(item["cells"])
    images = {c: item["qcow2"][c] for c in cells}
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "cycles").mkdir(exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(q2m, indent=2, sort_keys=True))
    write_preflight(run_dir, job_id, {"manifest_sha256": manifest_sha256(q2m), "ap_delta": "rung",
                                      "rung_cells": "+".join(cells)})  # fmt: skip
    receipt: dict[str, Any] = {
        "schema": "cotcodec-vm-campaign-receipt-v1", "job_id": job_id,
        "manifest_sha256": manifest_sha256(q2m), "campaign_id": q2m["campaign_id"],
        "git_sha": q2m["git_sha"], "source_tree_sha256": q2m["source"]["tree_sha256"],
        "started_at": time.time(), "driver_python": sys.version.split()[0],
        "ap_delta": {"rung_cells": cells, "assignment": "session i on cells[i % len(cells)]"},
    }  # fmt: skip
    rc = 3
    try:
        # driver.main's pre-run checks, with harness/q2's own functions and messages
        info = json.loads(driver.run([driver.DOCKER, "info", "--format", "{{json .}}"],
                                     timeout=60).stdout)  # fmt: skip
        receipt["docker"] = {"server_version": info.get("ServerVersion"),
                             "default_runtime": info.get("DefaultRuntime"),
                             "runtimes": sorted((info.get("Runtimes") or {}).keys()),
                             "cgroup_version": info.get("CgroupVersion")}  # fmt: skip
        vm = q2m["vm"]
        image_check = driver.run([driver.DOCKER, "image", "inspect", "--format",
                                  "{{.Id}} {{json .RepoDigests}}", vm["image_id"]],
                                 timeout=60).stdout.strip()  # fmt: skip
        if not image_check.startswith(vm["image_id"]) or vm["image"] not in image_check:
            raise driver.DriverError("VM image ID and digest reference do not agree")
        runner_id = driver.run([driver.DOCKER, "image", "inspect", "--format", "{{.Id}}",
                                q2m["runner"]["image_id"]], timeout=60).stdout.strip()  # fmt: skip
        if runner_id != q2m["runner"]["image_id"]:
            raise driver.DriverError("runner image is missing")
        before, qinfo = {}, {}
        for c, e in images.items():
            st = os.stat(e["host_path"], follow_symlinks=False)
            _require(os.path.isfile(e["host_path"]) and not os.path.islink(e["host_path"]),
                     f"{c}: image is not a regular file")  # fmt: skip
            _require(st.st_size == e["size_bytes"] and not st.st_mode & 0o222,
                     f"{c}: image size differs or it is writable")  # fmt: skip
            before[c] = driver.sha256_file(e["host_path"])
            _require(before[c] == e["sha256"], f"{c}: image digest differs")
            mine = dict(q2m, vm=dict(vm, qcow2=dict(e)))
            qimg = driver.run(driver.qemu_img_info_argv(mine, job_id), timeout=120)
            out = json.loads(qimg.stdout)
            qinfo[c] = {k: out.get(k) for k in ("format", "virtual-size", "actual-size")}
        receipt["qcow2_sha256_before"] = before
        receipt["qcow2_info"] = qinfo
        dangling = driver.run([driver.DOCKER, "volume", "ls", "-q", "--filter", "dangling=true"],
                              timeout=60)  # fmt: skip
        receipt["dangling_volumes_before"] = len(dangling.stdout.split())
        cells_data = json.loads((source_dir / CELLS_FILE).read_text(encoding="utf-8"))
        volume = json.loads((source_dir / VOLUME_PLAN).read_text(encoding="utf-8"))
        plan = (driver.acceptance_plan(q2m, cells_data, volume)
                if q2m["workload"]["kind"] == "suite-acceptance"
                else driver.session_plan(q2m, cells_data))  # a development rung
        (run_dir / "session_plan.json").write_text(json.dumps(plan, indent=1))
        from harness.q2.action_path import order as run_order

        receipt["session_plan_sha256"] = run_order.order_sha256(plan)
        allocated = driver.slurm_cpu_ids(job_id)
        slices = driver.plan_cpusets_multi(q2m, allocated, driver.numa_nodes())
        receipt["cpusets"] = slices
        receipt["host_start"] = driver.snapshot_host(job_id)
        image_of = {i: cells[i % len(cells)] for i in range(len(plan))}
        receipt["image_of_session"] = image_of
        by_cycle: dict[int, dict[str, Any]] = {}

        def worker(index: int) -> None:
            cell = cells[index % len(cells)]
            mine = dict(q2m, vm=dict(q2m["vm"], qcow2=dict(images[cell])))
            for cycle in range(index, len(plan), len(slices)):
                record = driver.run_cycle(mine, job_id, cycle, None, run_dir, str(source_dir),
                                          slices[index], session=plan[cycle])  # fmt: skip
                record["image_cell"] = cell
                by_cycle[cycle] = record
                (run_dir / "cycles" / f"record-{cycle:02d}.json").write_text(
                    json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")

        with ThreadPoolExecutor(max_workers=len(slices)) as pool:
            list(pool.map(worker, range(len(slices))))
        records = [by_cycle[c] for c in sorted(by_cycle)]
        verdicts = [driver.cycle_verdict(r, []) for r in records]
        after = {c: driver.sha256_file(e["host_path"]) for c, e in images.items()}
        receipt["qcow2_sha256_after"] = after
        receipt["qcow2_unchanged"] = after == before
        receipt["labelled_containers_left"] = docker(
            "ps", "-a", "--filter", f"label=cotcodec.slurm_job={job_id}", "--format",
            "{{.Names}}").stdout.split()  # fmt: skip
        dangling = driver.run([driver.DOCKER, "volume", "ls", "-q", "--filter", "dangling=true"],
                              timeout=60)  # fmt: skip
        receipt["dangling_volumes_after"] = len(dangling.stdout.split())
        receipt["host_end"] = driver.snapshot_host(job_id)
        summary = driver.summarize(verdicts, records)
        summary["sessions"] = driver.session_summary(records)
        summary["infra_gates_pass"] = (
            summary["boots_ok"] == summary["cycles"] and summary["no_gpu_all"]
            and summary["no_published_ports_all"] and summary["containers_removed_all"]
            and not summary["leaked_volumes"] and receipt["qcow2_unchanged"]
            and not receipt["labelled_containers_left"]
            and not summary["sessions"]["runner_errors"])  # fmt: skip
        receipt["summary"] = summary
        receipt["verdicts"] = verdicts
        rc = 0 if summary["infra_gates_pass"] else 3
    except (DeltaError, driver.DriverError) as exc:
        receipt["error"] = str(exc)[:500]
    receipt["finished_at"] = time.time()
    (run_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True))
    ids = docker("ps", "-aq", "--filter", f"label=cotcodec.slurm_job={job_id}").stdout.split()
    if ids:
        docker("rm", "--force", "--volumes", *ids, timeout=120)
    with (run_dir / "preflight.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"driver_exit={rc} labelled_containers_left={labelled_left(job_id)}\n")
    return rc


def run(m: Mapping[str, Any], run_dir: Path, source_dir: Path, job_id: str) -> dict[str, Any]:
    """Every campaign of the manifest, in order; a stop signal ends the job after the current
    campaign (the q2 driver is sent TERM, as vm-campaign.sbatch does on a signal)."""
    from harness.q2.vm.manifest import source_tree_sha256

    tree = source_tree_sha256(str(source_dir))
    for item in m["campaigns"]:
        source = item["manifest"]["source"]
        _require(source["host_dir"] == str(source_dir.resolve()) and source["tree_sha256"] == tree,
                 f"{item['manifest']['campaign_id']}: source is not this export")  # fmt: skip
    stop = [False]
    signal.signal(signal.SIGUSR1, lambda *_: stop.__setitem__(0, True))
    out = {"schema": "s2v4-apdelta-receipt-v1", "job_id": job_id, "check": m["check"],
           "purpose": m["purpose"], "campaigns": [], "t_start": time.time()}  # fmt: skip
    for k, item in enumerate(m["campaigns"]):
        if stop[0]:
            out["campaigns"].append({"campaign_id": item["manifest"]["campaign_id"],
                                     "status": "not_started"})  # fmt: skip
            continue
        sub = run_dir / f"{k:02d}-{item['manifest']['campaign_id']}"
        if is_rung(item):
            rc = run_rung(item, sub, source_dir, job_id)
        else:
            rc = run_campaign(item["manifest"], sub, source_dir, job_id,
                              60.0 * campaign_minutes(item["manifest"], image_bytes(
                                  {"campaigns": [item]})), stop)  # fmt: skip
        (sub / "apdelta.json").write_text(json.dumps({"check": m["check"],
                                                      "cells": item["cells"]}))  # fmt: skip
        out["campaigns"].append({"campaign_id": item["manifest"]["campaign_id"],
                                 "dir": sub.name, "cells": item["cells"], "driver_exit": rc})
    out["t_end"] = time.time()
    sha = source_dir / ".git_sha"
    out["executor_commit"] = sha.read_text().strip() if sha.is_file() else None
    (run_dir / "apdelta-receipt.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    return out


# --------------------------------------------------------------------------- verdict


def load_campaigns(job_dirs: Sequence[Path]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Every campaign run directory of the given ``ap_delta`` job directories (in job order),
    loaded by ``acceptance.load``; reruns of one campaign (same check, cells and campaign key) are
    attempts, the last one counting with the earlier ones attached (section 6.1)."""
    from harness.q2.action_path import acceptance as A

    groups: dict[tuple[str, str, str], list[Path]] = {}
    for job_dir in job_dirs:
        for sub in sorted(Path(job_dir).iterdir()):
            meta_path, man = sub / "apdelta.json", sub / "manifest.json"
            if not (meta_path.is_file() and man.is_file()):
                continue
            meta = json.loads(meta_path.read_text())
            key = (meta["check"], "+".join(meta["cells"]),
                   json.dumps(campaign_key(json.loads(man.read_text())), sort_keys=True))
            groups.setdefault(key, []).append(sub)
    out = {}
    for key, subs in groups.items():
        attempts: list[dict[str, Any]] = []
        for sub in subs:
            attempts.append(A.load(str(sub), earlier=list(attempts)))
        out[key] = attempts[-1]
    return out


def rung_verdict(rung: Sequence[Mapping[str, Any]],
                 a1_by_cell: Mapping[str, Sequence[Mapping[str, Any]]],
                 ) -> dict[str, Any]:  # fmt: skip
    """Section 9's rule at N = 20 (section "K1"): ``acceptance.rung`` for every condition but the
    step p95, which is read per image against that image's own A1 step p95."""
    from harness.q2.action_path import acceptance as A

    if not rung:
        return {"qualifies": False, "problems": ["no rung campaign"]}
    base = A.rung(list(rung), float("inf"))
    image_of: dict[str, str] = {}
    for c in rung:
        mapping = c["receipt"].get("image_of_session") or {}
        image_of.update({str(k): v for k, v in mapping.items()})
    per_image = {}
    for cell in RUNG_CELLS:
        a1 = [x for c in a1_by_cell.get(cell) or [] for s in c["sessions"] for t in s["trials"]
              for x in t["steps_s"]]  # fmt: skip
        mine = [x for c in rung for s in c["sessions"] if image_of.get(str(s["cycle"])) == cell
                for t in s["trials"] for x in t["steps_s"]]  # fmt: skip
        ref, p95 = A.quantile(a1, 0.95), A.quantile(mine, 0.95)
        ok = ref is not None and p95 is not None and p95 <= A.STEP_P95_FACTOR * ref
        per_image[cell] = {"step_p95_s": p95, "a1_step_p95_s": ref, "ok": ok,
                           "steps": len(mine)}  # fmt: skip
    problems = list(base["problems"]) + [
        f"{c}: step p95 {v['step_p95_s']} s > {A.STEP_P95_FACTOR} x {v['a1_step_p95_s']} s"
        for c, v in per_image.items() if not v["ok"]]
    return {**base, "problems": problems, "per_image_step": per_image,
            "qualifies": not problems and not base["aborted"]}  # fmt: skip


def verdict(job_dirs: Sequence[Path], freeze_sha: str) -> dict[str, Any]:
    """K1 from the jobs' run directories: per image every check by ``acceptance``'s own
    functions (C1-C4, A1, A2, A5, A6; A3 in AR), and the rung."""
    from harness.q2.action_path import acceptance as A

    loaded = load_campaigns(job_dirs)

    def get(check: str, cell: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        return [(json.loads(k[2]), c) for k, c in loaded.items() if k[0] == check and k[1] == cell]

    per_cell: dict[str, dict[str, Any]] = {}
    for cell in K1_CELLS:
        a1_by_seed = {key["seed"]: [c] for key, c in get("A1", cell)}
        checks = {
            "C1": A.c1({key["layer"]: [c] for key, c in get("C1", cell)}),
            "C2": A.c2([c for _, c in get("C2", cell)]),
            "C3": A.c3({(key["mutant"], key["layer"]): [c] for key, c in get("C3", cell)
                        if key["mutant"] != "none"},
                       {key["layer"]: [c] for key, c in get("C3", cell)
                        if key["mutant"] == "none"}),
            "C4": A.c4([c for cs in a1_by_seed.values() for c in cs]),
            "A1": A.a1(a1_by_seed),
            "A2": A.a2({key["layer"]: [c] for key, c in get("A2", cell)}),
            "A6": A.a6([c for _, c in get("A6", cell)]),
            "A5": A.a5(next((c for _, c in get("A5", cell)), None),
                       [c for k, c in loaded.items() if k[1] == cell and k[0] != "A5"],
                       freeze_sha),
        }  # fmt: skip
        if cell == "AR":
            checks["A3"] = A.a3({key["layer"]: [c] for key, c in get("A3", cell)})
        per_cell[cell] = checks
    rung = rung_verdict([c for _, c in get("rung", "+".join(RUNG_CELLS))],
                        {cell: [c for _, c in get("A1", cell)] for cell in K1_CELLS})
    passes = (all(v.get("pass") for checks in per_cell.values() for v in checks.values())
              and rung["qualifies"])  # fmt: skip
    return {"schema": "s2v4-k1-verdict-v1", "K1": "PASS" if passes else "FAIL",
            "per_image": {c: {k: {"pass": v.get("pass"), "problems": v.get("problems")}
                              for k, v in checks.items()} for c, checks in per_cell.items()},
            "rung": rung, "details": per_cell}  # fmt: skip


# --------------------------------------------------------------------------- render (Mac)


def swap_disk(q2m: Mapping[str, Any], cell: str, pins: Mapping[str, Any],
              images_root: str) -> dict[str, Any]:  # fmt: skip
    """The q2 manifest with ``vm.qcow2`` naming the cell image (provenance: the certified disk)."""
    out = json.loads(json.dumps(q2m))
    out["vm"]["qcow2"] = {"host_path": f"{images_root}/s2v4-cell-{cell}.qcow2",
                          "sha256": pins[cell]["sha256"], "size_bytes": pins[cell]["size_bytes"],
                          **CERTIFIED_PROVENANCE}  # fmt: skip
    return out


def render_campaign(entry: Mapping[str, Any], cell: str, args: argparse.Namespace,
                    pins: Mapping[str, Any]) -> dict[str, Any]:  # fmt: skip
    """One K1 campaign: q2's own renderer (scripts/render_q2_action_path_manifest.py) for the
    criterion, then the disk swapped to the cell image and q2's validator run again."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import render_q2_action_path_manifest as R  # noqa: PLC0415

    criterion = {"boot-reset-validation": "A5", "canary-acceptance": "A6"}.get(
        entry["kind"], entry.get("criterion"))  # fmt: skip
    slug = re.sub(r"[^a-z0-9]+", "-", f"s2v4-k1-{cell}-{entry.get('criterion') or criterion}-"
                  f"{entry.get('layer') or ''}-{entry.get('mutant') or ''}-"
                  f"{entry.get('seed') or ''}".lower()).strip("-")[:63]  # fmt: skip
    ns = argparse.Namespace(
        criterion=criterion, source_dir=args.source_dir, git_sha=args.git_sha,
        host_root=args.host_root, seed=entry.get("seed") or 43, layer=entry.get("layer"),
        concurrency=entry["concurrency"], runner_cpus=None, session_range=None,
        mutant=entry.get("mutant"), attempt=1, max_trial_s=30, name="s2v4-k1",
        campaign_id=slug)  # fmt: skip
    if entry["concurrency"] == RUNG_N:  # q2's renderer refuses N = 20: render at 24, then set 20
        from harness.q2.vm.manifest import ladder_reps, runner_cpus

        ns.concurrency = RUNG_SHADOW_N
        q2m = R.render(ns)
        q2m["vm"]["concurrency"] = RUNG_N
        q2m["workload"]["reps"] = ladder_reps(RUNG_N)
        q2m["runner"]["cpus"] = runner_cpus(RUNG_N)
        sessions, trials = plan_counts(q2m, Path(args.source_dir))
        q2m["workload"].update(sessions=sessions, trials=trials)
        budget = 600 + (sessions * (300 + 60 + 240) + trials * ns.max_trial_s) / RUNG_N
        q2m["slurm"] = {"cpus": RUNG_N * 4 + runner_cpus(RUNG_N),
                        "memory_gb": RUNG_N * (q2m["vm"]["memory_gb"] + 1) + 2,
                        "minutes": int(math.ceil(budget / 600.0) * 10)}  # fmt: skip
        return q2m
    q2m = R.render(ns)
    return swap_disk(q2m, cell, pins, args.images_root)


DEV_CELLS = ("click_left_center", "type_plain", "key_enter")


def dev_campaign(args: argparse.Namespace, pins: Mapping[str, Any], cells: Sequence[str],
                 concurrency: int, settings: Sequence[str],
                 cid: str) -> dict[str, Any]:  # fmt: skip
    """A q2 development campaign (seed 42, a few L0-fixed entries) on cell images, the shape of
    harness/q2's own development manifests (TEMPLATE's VM and runner pins)."""
    import yaml

    from harness.q2.vm import driver
    from harness.q2.vm.manifest import ledger_view, source_tree_sha256

    root = Path(__file__).resolve().parents[2]
    template = yaml.safe_load((root / "experiments/manifests/q2-action-path/dev-l0-fixed-v10.yaml")
                              .read_text())  # fmt: skip
    source = Path(args.source_dir)
    rows = ledger_view(str(source), [])["rows"]
    cells_bytes = (source / CELLS_FILE).read_bytes()
    q2m: dict[str, Any] = {
        "schema": template["schema"], "name": "s2v4-apd-dev", "campaign_id": cid,
        "experiment_id": "q2-action-path-v2", "purpose": "development",
        "preregistration": {"path": "program/preregistrations/q2-action-path-v2.md",
                            "status": "frozen",
                            "sha256": rows["q2-action-path-v2"]["sha256"]},
        "git_sha": args.git_sha,
        "source": {"host_dir": f"{args.host_root}/src/{args.git_sha}",
                   "tree_sha256": source_tree_sha256(str(source))},
        "run_root": f"{args.host_root}/runs", "slurm": {},
        "container_profile": template["container_profile"],
        "model": {"kind": "none", "reason": "an S2 v4 ap_delta development run of the action-path "
                                            "executor on cell images loads no model"},
        "randomness": {"contract": "seeded", "seeds": [42], "seed_binding": {"flag": "--seed"}},
        "vm": dict(copy.deepcopy(template["vm"]), concurrency=concurrency),
        "runner": dict(template["runner"], cpus=max(1, -(-concurrency // 2))),
        "workload": {"kind": "suite-development", "layer": "L0-fixed", "cells": list(DEV_CELLS),
                     "reps": 1, "settings": list(settings), "session_trials": 60,
                     "boot_timeout_s": 300, "settle_timeout_s": 60,
                     "cells_sha256": hashlib.sha256(cells_bytes).hexdigest(),
                     "sessions": 0, "trials": 0, "max_trial_s": 60},
    }  # fmt: skip
    plan = driver.session_plan(q2m, json.loads(cells_bytes))
    q2m["workload"].update(sessions=len(plan), trials=sum(len(x["trials"]) for x in plan))
    budget = 600 + len(plan) * (300 + 60 + 240) + q2m["workload"]["trials"] * 60
    q2m["slurm"] = {"cpus": concurrency * 4 + q2m["runner"]["cpus"],
                    "memory_gb": concurrency * 7 + 2, "minutes": int(math.ceil(budget / 600) * 10)}
    q2m = swap_disk(q2m, cells[0], pins, args.images_root)
    item: dict[str, Any] = {"cells": list(cells), "manifest": q2m}
    if len(cells) > 1:
        item["qcow2"] = {c: swap_disk(q2m, c, pins, args.images_root)["vm"]["qcow2"]
                         for c in cells}  # fmt: skip
    return item


def render_dev(args: argparse.Namespace) -> dict[str, Any]:
    """The development manifest: one single-image campaign on E (the q2 driver unchanged, one
    session) and one development rung over E and AR at N = 2 (two sessions, one per image)."""
    source = Path(args.source_dir)
    pins = L.load_pins(source)
    items = [dev_campaign(args, pins, ["E"], 1, ["screenshot"], "s2v4-apd-dev-single"),
             dev_campaign(args, pins, ["E", "AR"], 2, ["screenshot", "screenshot+a11y"],
                          "s2v4-apd-dev-rung")]  # fmt: skip
    m = {"schema": SCHEMA, "experiment_id": EXPERIMENT_ID, "purpose": "development",
         "name": "apd-dev-v1", "check": "rung", "run_root": f"{args.host_root}/runs",
         "campaigns": items}  # fmt: skip
    total = 10 + sum(campaign_minutes(i["manifest"], image_bytes({"campaigns": [i]}))
                     for i in items)  # fmt: skip
    m["slurm"] = {"cpus": max(int(i["manifest"]["slurm"]["cpus"]) for i in items),
                  "memory_gb": max(int(i["manifest"]["slurm"]["memory_gb"]) for i in items),
                  "minutes": total}  # fmt: skip
    validate_manifest(m, source)
    return m


MAX_JOB_MINUTES = 1440


def render_k1(args: argparse.Namespace) -> list[dict[str, Any]]:
    """The ``k1`` manifests of one check on one cell (or the rung), from the freeze export, with
    the freeze commit checked with git and every campaign validated as the job will: one manifest,
    or numbered parts when the campaigns' budgets exceed one job's limit (C3, A3)."""
    source = Path(args.source_dir)
    row = L.frozen_registration(source)
    L.check_freeze_commit(args.repo, args.git_sha, row)
    pins = L.load_pins(source)
    plan = load_k1_plan(source)
    cells = list(RUNG_CELLS) if args.check == "rung" else [args.cell]
    key = "+".join(cells)
    entries = [e for e in plan if e["check"] == args.check and e["cell"] == key]
    _require(bool(entries), f"the K1 plan has no {args.check} campaigns on {key}")
    items = []
    for entry in entries:
        q2m = render_campaign(entry, cells[0], args, pins)
        item: dict[str, Any] = {"cells": cells, "manifest": q2m}
        if args.check == "rung":
            item["manifest"] = swap_disk(q2m, cells[0], pins, args.images_root)
            item["qcow2"] = {c: swap_disk(q2m, c, pins, args.images_root)["vm"]["qcow2"]
                             for c in cells}  # fmt: skip
        items.append(item)
    parts: list[list[dict[str, Any]]] = [[]]
    used = 10
    for item in items:
        need = campaign_minutes(item["manifest"], image_bytes({"campaigns": [item]}))
        if parts[-1] and used + need > MAX_JOB_MINUTES:
            parts.append([])
            used = 10
        parts[-1].append(item)
        used += need
    out = []
    for k, chunk in enumerate(parts, 1):
        name = f"k1-{args.check.lower()}-{key.replace('+', '').lower()}"
        m: dict[str, Any] = {
            "schema": SCHEMA, "experiment_id": EXPERIMENT_ID, "purpose": "k1",
            "name": (name if len(parts) == 1 else f"{name}-p{k}")[:60], "check": args.check,
            "run_root": f"{args.host_root}/runs", "campaigns": chunk,
            "freeze": {"commit": args.git_sha, "ledger_row_hash": row["hash"],
                       "git_head_at_freeze": row["git_head_at_freeze"]}}  # fmt: skip
        if len(parts) > 1:
            m["part"] = {"index": k, "of": len(parts)}
        if args.check == "rung":
            q2m = chunk[0]["manifest"]
            cpus = RUNG_N * q2m["vm"]["cpu_cores"] + q2m["runner"]["cpus"]
            mem = RUNG_N * (q2m["vm"]["memory_gb"] + 1) + 2
        else:
            cpus = max(int(i["manifest"]["slurm"]["cpus"]) for i in chunk)
            mem = max(int(i["manifest"]["slurm"]["memory_gb"]) for i in chunk)
        total = 10 + sum(campaign_minutes(i["manifest"], image_bytes({"campaigns": [i]}))
                         for i in chunk)  # fmt: skip
        m["slurm"] = {"cpus": cpus, "memory_gb": mem, "minutes": total}
        validate_manifest(m, source)
        out.append(m)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--manifest", type=Path, required=True)
    r.add_argument("--run-dir", type=Path, required=True)
    r.add_argument("--source-dir", type=Path, required=True)
    r.add_argument("--job-id", required=True)
    v = sub.add_parser("validate")
    v.add_argument("manifest", type=Path)
    v.add_argument("--source-dir", type=Path, default=Path("."))
    s = sub.add_parser("submit")
    s.add_argument("manifest", type=Path)
    s.add_argument("--source-dir", type=Path, default=Path("."))
    s.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("plan", help="the K1 plan file (Mac; needs PyYAML)")
    p.add_argument("--out", type=Path, required=True)
    rk = sub.add_parser("render", help="a K1 manifest for one check and cell (Mac; PyYAML)")
    rk.add_argument("check", choices=CHECKS)
    rk.add_argument("--cell", default=None, help="the cell image (not for the rung)")
    rk.add_argument("--source-dir", type=Path, required=True, help="export of the freeze commit")
    rk.add_argument("--git-sha", required=True)
    rk.add_argument("--repo", type=Path, default=Path("."))
    rk.add_argument("--host-root", default=K1_ROOT)
    rk.add_argument("--images-root", required=True, help="host directory of the cell images")
    rk.add_argument("--out", type=Path, required=True)
    vd = sub.add_parser("verdict", help="K1 from the ap_delta job directories")
    vd.add_argument("jobs", type=Path, nargs="+")
    vd.add_argument("--freeze-commit", required=True)
    vd.add_argument("--out", type=Path, required=True)
    rd = sub.add_parser("render-dev", help="the development manifest (Mac; PyYAML)")
    rd.add_argument("--source-dir", type=Path, required=True)
    rd.add_argument("--git-sha", required=True)
    rd.add_argument("--host-root", default=f"{RUN_ROOT}stage0/s2v4/apdelta-dev")
    rd.add_argument("--images-root", required=True)
    rd.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "verdict":
        out = verdict(args.jobs, args.freeze_commit)
        args.out.write_text(json.dumps(out, indent=1, sort_keys=True, default=str))
        print(json.dumps({"K1": out["K1"], "rung_qualifies": out["rung"]["qualifies"]}))
        return 0
    if args.command == "render-dev":
        m = render_dev(args)
        args.out.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
        print(json.dumps({"campaigns": len(m["campaigns"]), **check_slurm(m)}))
        return 0
    if args.command == "render":
        manifests = render_k1(args)
        for m in manifests:
            out = (args.out if len(manifests) == 1 else
                   args.out.with_name(f"{args.out.stem}-p{m['part']['index']}{args.out.suffix}"))
            out.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
            print(json.dumps({"check": m["check"], "part": m.get("part"), "out": out.name,
                              "campaigns": len(m["campaigns"]), **check_slurm(m)}))  # fmt: skip
        return 0
    if args.command == "plan":
        import yaml

        ops = yaml.safe_load(Path("harness/q2/action_path/mutation_operators.yaml").read_text())
        plan = {"schema": "s2v4-k1-plan-v1", "campaigns": k1_plan_entries(ops)}
        args.out.write_text(json.dumps(plan, indent=1, sort_keys=True) + "\n")
        print(json.dumps({"campaigns": len(plan["campaigns"])}))
        return 0
    if args.command == "validate":
        m = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
        print(json.dumps({"ok": True, "check": m["check"], "campaigns": len(m["campaigns"]),
                          **check_slurm(m)}))  # fmt: skip
        return 0
    if args.command == "submit":
        print(json.dumps(submit(args.manifest, args.source_dir, args.dry_run), indent=1))
        return 0
    if not re.fullmatch(r"[1-9][0-9]{0,19}", args.job_id):
        raise SystemExit("job id must be numeric")
    m = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
    out = run(m, args.run_dir, args.source_dir, args.job_id)
    print(json.dumps({"campaigns": [(c["campaign_id"], c.get("driver_exit"))
                                    for c in out["campaigns"]]}))  # fmt: skip
    return 0 if all(c.get("driver_exit") == 0 for c in out["campaigns"]) else 3


def submit(manifest_path: Path, source_dir: Path, dry_run: bool) -> dict[str, Any]:
    from harness.q2_stage1 import lane as s1a

    m = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), source_dir)
    request = check_slurm(m)
    text = L.canonical(m)
    digest = hashlib.sha256(text.encode()).hexdigest()
    run_root = Path(m["run_root"])
    stored = run_root / "manifests" / f"{digest}.json"
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_text(text, encoding="utf-8")
    batch = source_dir / BATCH
    env = {
        "COTCODEC_S2V4_MANIFEST_PATH_HEX": str(stored).encode().hex(),
        "COTCODEC_S2V4_MANIFEST_SHA256": digest,
        "COTCODEC_BATCH_SHA256": s1a.sha256_file(batch),
        "COTCODEC_SOURCE_HOST_HEX": str(source_dir.resolve()).encode().hex(),
        "COTCODEC_SOURCE_TREE_SHA256": s1a.tree_sha256(source_dir),
        "COTCODEC_RUN_ROOT_HEX": str(run_root).encode().hex(),
    }
    hours, mins = divmod(request["minutes"], 60)
    argv = ["sbatch", "--parsable", f"--cpus-per-task={request['cpus']}",
            f"--mem={request['memory_gb']}G", f"--time={hours:02d}:{mins:02d}:00",
            f"--job-name=s2v4-apd-{m['name']}"[:60],
            "--export=ALL," + ",".join(f"{k}={v}" for k, v in env.items()), str(batch)]  # fmt: skip
    out = {"manifest_sha256": digest, "manifest": str(stored), "argv": argv, **request}
    if not dry_run:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=True)
        out["job_id"] = done.stdout.strip()
    return out


if __name__ == "__main__":
    raise SystemExit(main())
