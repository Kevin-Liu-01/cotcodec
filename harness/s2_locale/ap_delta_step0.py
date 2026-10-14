"""S2 v5 step 0 (decision D94): ap_delta's development renderer extended to A6's canary.

Step 0 is one CPU-only development job under the unfrozen id ``s2-arabic-cua-locale-v5``: ONE
q2 ``canary-development`` campaign per cell image (E, A, ER, AR, PL), each with ``measure_targets``
true, seed 42, Writer, Chrome and VS Code, the two pointer composites (``triple_click_line``,
``drag_select_word``), 5 repetitions cut into sessions of 6 trials, so 5 cold boots per image, each
running every (app, entry) pair once. The actions use q2's frozen targets (``suite_cells.json``,
unchanged), so on ER and AR step 0 repeats v4's failing drag with screenshots; q2's measure mode
saves the screen before each pointer composite (from which ``canary_targets_v5`` measures the
fixture line) and after it, and records the AT-SPI extents (disclosure only).

It extends ``ap_delta`` without editing it: ``ap_delta.py`` is pinned by v4's frozen registration,
and its ``validate_manifest`` admits only v4's id, which is frozen, so development no longer runs
there (D56). This module reuses ap_delta's pieces (``swap_disk``, ``check_image_entry``,
``q2_validate``, ``campaign_minutes``, ``write_preflight``, ``labelled_left``) and harness/q2's
driver functions, unchanged.

One change from ``ap_delta.run_campaign``, and why. q2's measure mode names each screenshot
``canary-<trial>-<app>-<entry>.png`` in the campaign's ``cycles/`` directory, and the trial number
restarts in every session, so the 5 boots of one campaign would overwrite one another's
screenshots. ``run_canary`` is therefore driver.main's single-VM branch run in this process (as
``ap_delta.run_rung`` runs its concurrent branch): the same pre-run checks with harness/q2's own
functions and messages, ``driver.run_cycle`` unchanged for each session in order, and, after each
session, its screenshots moved into ``cycles/shots-NN/`` with their SHA-256 in the session's record.
Nothing inside a session changes.

The q2 campaign manifests are admitted by harness/q2's validator (``ap_delta.q2_validate``): purpose
``development``, the frozen ``q2-action-path-v2`` registration, no model, seed 42, one VM at a time.
The job holds no GPU: the batch file (``s2v5-step0.sbatch``) has no GRES line and refuses a GPU
allocation, the sbatch request names CPUs, memory and minutes only, and harness/q2's runner asserts
that it sees no NVIDIA device.

Commands: ``render`` (Mac; PyYAML), ``validate``, ``submit`` (host; ``--dry-run`` writes nothing),
``run`` (inside the job). Standard library only on the host.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.s2_locale import ap_delta as D
from harness.s2_locale import canary_targets_v5 as R
from harness.s2_locale import vm_lane as L

SCHEMA = "s2v5-step0-v1"
EXPERIMENT_ID = "s2-arabic-cua-locale-v5"
V4_ID = L.EXPERIMENT_ID
CHECK = "step0"
CELLS = R.CELLS
APPS = R.APPS
ENTRIES = R.ENTRIES
HOST_ROOT = f"{L.RUN_ROOT}stage0/s2v5/step0"
IMAGES_ROOT = f"{L.RUN_ROOT}stage0/s2v4/image-build-v5/a"
BATCH = "infra/slurm/host-single-node/s2v5-step0.sbatch"
TEMPLATE = "experiments/manifests/q2-action-path/dev-l0-fixed-v10.yaml"
# The q2 workload of every step-0 campaign (q2's own canary development values: boot 300 s,
# settle 60 s, 90 s per trial, as dev-canary-v5 to v12).
WORKLOAD = {
    "kind": "canary-development",
    "apps": list(APPS),
    "entries": list(ENTRIES),
    "reps": R.BOOTS,
    "session_trials": len(APPS) * len(ENTRIES),
    "measure_targets": True,
    "boot_timeout_s": 300,
    "settle_timeout_s": 60,
    "max_trial_s": 90,
}
SESSIONS = R.BOOTS
TRIALS = R.BOOTS * len(APPS) * len(ENTRIES)
SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")


class Step0Error(ValueError):
    """The manifest is not step 0's; nothing may start."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Step0Error(message)


# --------------------------------------------------------------------------- ledger


def ledger_row(source_dir: Path, experiment_id: str) -> dict[str, Any] | None:
    """``experiment_id``'s ledger row after checking the hash chain (as ``vm_lane.ledger_row``)."""
    ledger = source_dir / L.LEDGER
    if not ledger.is_file():
        return None
    previous, row = "0" * 64, None
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        entry = json.loads(line)
        body = {k: v for k, v in entry.items() if k != "hash"}
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        _require(
            entry.get("previous_hash") == previous and entry.get("hash") == digest,
            f"ledger line {number}: the hash chain does not hold",
        )
        previous = digest
        if row is None and entry.get("experiment_id") == experiment_id:
            row = entry
    return row


# --------------------------------------------------------------------------- render (Mac)


def canary_campaign(args: argparse.Namespace, pins: Mapping[str, Any], cell: str) -> dict[str, Any]:
    """One q2 canary-development campaign on ``cell``'s image (the shape of ap_delta's
    ``dev_campaign``: TEMPLATE's VM and runner pins, the frozen q2-action-path-v2 registration)."""
    import yaml

    from harness.q2.vm import driver
    from harness.q2.vm.manifest import ledger_view, source_tree_sha256

    root = Path(__file__).resolve().parents[2]
    template = yaml.safe_load((root / TEMPLATE).read_text())
    source = Path(args.source_dir)
    rows = ledger_view(str(source), [])["rows"]
    cells_bytes = (source / D.CELLS_FILE).read_bytes()
    q2m: dict[str, Any] = {
        "schema": template["schema"],
        "name": "s2v5-step0",
        "campaign_id": f"s2v5-step0-{cell.lower()}",
        "experiment_id": "q2-action-path-v2",
        "purpose": "development",
        "preregistration": {
            "path": "program/preregistrations/q2-action-path-v2.md",
            "status": "frozen",
            "sha256": rows["q2-action-path-v2"]["sha256"],
        },
        "git_sha": args.git_sha,
        "source": {
            "host_dir": f"{args.host_root}/src/{args.git_sha}",
            "tree_sha256": source_tree_sha256(str(source)),
        },
        "run_root": f"{args.host_root}/runs",
        "slurm": {},
        "container_profile": template["container_profile"],
        "model": {
            "kind": "none",
            "reason": "S2 v5 step 0 measures the canary's fixture line on cell images; "
            "the action-path executor loads no model",
        },
        "randomness": {"contract": "seeded", "seeds": [42], "seed_binding": {"flag": "--seed"}},
        "vm": dict(copy.deepcopy(template["vm"]), concurrency=1),
        "runner": dict(template["runner"], cpus=1),
        "workload": dict(
            WORKLOAD,
            cells_sha256=hashlib.sha256(cells_bytes).hexdigest(),
            sessions=0,
            trials=0,
        ),
    }
    plan = driver.session_plan(q2m, json.loads(cells_bytes))
    w = q2m["workload"]
    w.update(sessions=len(plan), trials=sum(len(s["trials"]) for s in plan))
    budget = 600 + w["sessions"] * (w["boot_timeout_s"] + w["settle_timeout_s"] + 240)
    budget += w["trials"] * w["max_trial_s"]
    q2m["slurm"] = {
        "cpus": q2m["vm"]["cpu_cores"] + q2m["runner"]["cpus"],
        "memory_gb": q2m["vm"]["memory_gb"] + 3,
        "minutes": int(math.ceil(budget / 600) * 10),
    }
    q2m = D.swap_disk(q2m, cell, pins, args.images_root)
    return {"cells": [cell], "manifest": q2m}


def render(args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.source_dir)
    pins = L.load_pins(source)
    items = [canary_campaign(args, pins, cell) for cell in CELLS]
    m: dict[str, Any] = {
        "schema": SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "purpose": "development",
        "check": CHECK,
        "name": "step0-canary-v1",
        "run_root": f"{args.host_root}/runs",
        "campaigns": items,
    }
    m["slurm"] = {
        "cpus": max(int(i["manifest"]["slurm"]["cpus"]) for i in items),
        "memory_gb": max(int(i["manifest"]["slurm"]["memory_gb"]) for i in items),
        "minutes": budget_minutes(m),
    }
    validate_manifest(m, source)
    return m


# --------------------------------------------------------------------------- validation


def budget_minutes(m: Mapping[str, Any]) -> int:
    """10 + every campaign's own q2 budget and its two image checks (ap_delta's rule)."""
    return 10 + sum(
        D.campaign_minutes(item["manifest"], item["manifest"]["vm"]["qcow2"]["size_bytes"])
        for item in m["campaigns"]
    )


def check_slurm(m: Mapping[str, Any]) -> dict[str, int]:
    """CPUs, memory and minutes only (no other key, so no GPU can be requested)."""
    slurm = m.get("slurm") or {}
    _require(set(slurm) == {"cpus", "memory_gb", "minutes"}, "slurm: cpus, memory_gb, minutes")
    need_cpus = max(int(i["manifest"]["slurm"]["cpus"]) for i in m["campaigns"])
    need_mem = max(int(i["manifest"]["slurm"]["memory_gb"]) for i in m["campaigns"])
    total = budget_minutes(m)
    cpus, memory, minutes = slurm["cpus"], slurm["memory_gb"], slurm["minutes"]
    _require(isinstance(cpus, int) and need_cpus <= cpus <= 16, f"slurm.cpus {need_cpus}-16")
    _require(isinstance(memory, int) and need_mem <= memory <= 64, f"slurm.memory_gb >= {need_mem}")
    _require(
        isinstance(minutes, int) and total <= minutes <= 1440,
        f"slurm.minutes must cover every campaign and its image checks ({total})",
    )
    return {"cpus": cpus, "memory_gb": memory, "minutes": minutes, "budget_minutes": total}


def validate_manifest(raw: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    m = json.loads(json.dumps(raw))
    _require(m.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    _require(m.get("experiment_id") == EXPERIMENT_ID, f"experiment_id must be {EXPERIMENT_ID}")
    _require(m.get("purpose") == "development", "step 0 is development")
    _require(m.get("check") == CHECK, f"check must be {CHECK}")
    _require(
        ledger_row(source_dir, EXPERIMENT_ID) is None,
        f"{EXPERIMENT_ID} is frozen: development no longer runs (D56)",
    )
    _require(ledger_row(source_dir, V4_ID) is not None, f"step 0 follows the frozen {V4_ID} (D94)")
    _require(isinstance(m.get("name"), str) and bool(SAFE.fullmatch(m["name"])), "unsafe name")
    _require(str(m.get("run_root", "")).startswith(HOST_ROOT), f"run_root outside {HOST_ROOT}")
    campaigns = m.get("campaigns") or []
    _require(
        [item.get("cells") for item in campaigns] == [[c] for c in CELLS],
        f"one campaign per image, in the order {list(CELLS)}",
    )
    pins = L.load_pins(source_dir)
    cells_sha = hashlib.sha256((source_dir / D.CELLS_FILE).read_bytes()).hexdigest()
    sha_file = source_dir / ".git_sha"
    export_sha = sha_file.read_text(encoding="utf-8").strip() if sha_file.is_file() else None
    seen: set[str] = set()
    for item in campaigns:
        q2m = item.get("manifest") or {}
        cid = str(q2m.get("campaign_id"))
        _require(cid not in seen, f"campaign {cid} twice")
        seen.add(cid)
        _require(set(item) == {"cells", "manifest"}, f"{cid}: one image per campaign")
        try:
            D.check_image_entry(q2m, item["cells"][0], pins)
        except D.DeltaError as exc:
            raise Step0Error(str(exc)) from exc
        _require(q2m.get("purpose") == "development", f"{cid}: a development campaign")
        _require(q2m.get("experiment_id") == "q2-action-path-v2", f"{cid}: q2-action-path-v2")
        _require((q2m.get("model") or {}).get("kind") == "none", f"{cid}: no model")
        _require((q2m.get("vm") or {}).get("concurrency") == 1, f"{cid}: one VM at a time")
        w = q2m.get("workload") or {}
        _require(
            {k: w.get(k) for k in WORKLOAD} == WORKLOAD,
            f"{cid}: the workload is not step 0's ({WORKLOAD})",
        )
        _require(
            (w.get("sessions"), w.get("trials")) == (SESSIONS, TRIALS),
            f"{cid}: {SESSIONS} boots of {TRIALS // SESSIONS} trials",
        )
        _require(w.get("cells_sha256") == cells_sha, f"{cid}: suite_cells.json is not q2's")
        _require((q2m.get("randomness") or {}).get("seeds") == [42], f"{cid}: seed 42")
        _require(
            str(q2m.get("run_root", "")).startswith(HOST_ROOT), f"{cid}: run_root outside step 0"
        )
        try:
            D.q2_validate(q2m, source_dir)
        except D.DeltaError as exc:
            raise Step0Error(str(exc)) from exc
        if export_sha is not None:
            _require(q2m.get("git_sha") == export_sha, f"{cid}: git_sha is not the export's")
    check_slurm(m)
    return m


# --------------------------------------------------------------------------- run (in the job)


def keep_screenshots(cycles_dir: Path, cycle: int) -> dict[str, str]:
    """Move the session's measure-mode screenshots into ``shots-NN/`` (name -> SHA-256)."""
    dest = cycles_dir / f"shots-{cycle:02d}"
    dest.mkdir(exist_ok=True)
    kept = {}
    for path in sorted(cycles_dir.glob("canary-*.png")):
        kept[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.move(str(path), str(dest / path.name))
    return kept


def run_canary(
    item: Mapping[str, Any], run_dir: Path, source_dir: Path, job_id: str, stop: list[bool]
) -> int:
    """driver.main's single-VM branch for one step-0 campaign, keeping each boot's screenshots."""
    from harness.q2.action_path import order as run_order
    from harness.q2.vm import driver
    from harness.q2.vm.manifest import manifest_sha256

    q2m = dict(item["manifest"])
    vm, qcow2 = q2m["vm"], q2m["vm"]["qcow2"]
    cycles_dir = run_dir / "cycles"
    cycles_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "manifest.json").write_text(json.dumps(q2m, indent=2, sort_keys=True))
    D.write_preflight(
        run_dir, job_id, {"manifest_sha256": manifest_sha256(q2m), "ap_delta": "step0"}
    )
    receipt: dict[str, Any] = {
        "schema": "cotcodec-vm-campaign-receipt-v1",
        "job_id": job_id,
        "manifest_sha256": manifest_sha256(q2m),
        "campaign_id": q2m["campaign_id"],
        "git_sha": q2m["git_sha"],
        "source_tree_sha256": q2m["source"]["tree_sha256"],
        "started_at": time.time(),
        "driver_python": sys.version.split()[0],
        "ap_delta": {"step0": True, "cell": item["cells"][0]},
    }
    rc = 3
    try:
        # driver.main's pre-run checks, with harness/q2's own functions and messages
        info = json.loads(
            driver.run([driver.DOCKER, "info", "--format", "{{json .}}"], timeout=60).stdout
        )
        receipt["docker"] = {
            "server_version": info.get("ServerVersion"),
            "default_runtime": info.get("DefaultRuntime"),
            "runtimes": sorted((info.get("Runtimes") or {}).keys()),
            "cgroup_version": info.get("CgroupVersion"),
        }
        image_check = driver.run(
            [driver.DOCKER, "image", "inspect", "--format", "{{.Id}} {{json .RepoDigests}}",
             vm["image_id"]], timeout=60,
        ).stdout.strip()  # fmt: skip
        if not image_check.startswith(vm["image_id"]) or vm["image"] not in image_check:
            raise driver.DriverError("VM image ID and digest reference do not agree")
        runner_id = driver.run(
            [driver.DOCKER, "image", "inspect", "--format", "{{.Id}}", q2m["runner"]["image_id"]],
            timeout=60,
        ).stdout.strip()
        if runner_id != q2m["runner"]["image_id"]:
            raise driver.DriverError("runner image is missing")
        stat = os.stat(qcow2["host_path"], follow_symlinks=False)
        if not os.path.isfile(qcow2["host_path"]) or os.path.islink(qcow2["host_path"]):
            raise driver.DriverError("qcow2 must be a regular file")
        if stat.st_size != qcow2["size_bytes"]:
            raise driver.DriverError("qcow2 size does not match the manifest")
        if stat.st_mode & 0o222:
            raise driver.DriverError("qcow2 must be read-only on the host")
        receipt["qcow2_sha256_before"] = driver.sha256_file(qcow2["host_path"])
        if receipt["qcow2_sha256_before"] != qcow2["sha256"]:
            raise driver.DriverError("qcow2 digest does not match the manifest")
        qinfo = json.loads(driver.run(driver.qemu_img_info_argv(q2m, job_id), timeout=120).stdout)
        receipt["qcow2_info"] = {k: qinfo.get(k) for k in ("format", "virtual-size", "actual-size")}
        cpus = driver.plan_cpusets(q2m, driver.slurm_cpu_ids(job_id), driver.numa_nodes())
        receipt["cpusets"] = cpus
        receipt["host_start"] = driver.snapshot_host(job_id)
        dangling = driver.run(
            [driver.DOCKER, "volume", "ls", "-q", "--filter", "dangling=true"], timeout=60
        )
        receipt["dangling_volumes_before"] = len(dangling.stdout.split())
        cells_path = source_dir / driver.CELLS
        if hashlib.sha256(cells_path.read_bytes()).hexdigest() != q2m["workload"]["cells_sha256"]:
            raise driver.DriverError("suite_cells.json digest does not match the manifest")
        plan = driver.session_plan(q2m, json.loads(cells_path.read_text(encoding="utf-8")))
        trials = sum(len(s["trials"]) for s in plan)
        if (len(plan), trials) != (q2m["workload"]["sessions"], q2m["workload"]["trials"]):
            raise driver.DriverError(
                f"plan has {len(plan)} sessions and {trials} trials; the manifest declares "
                f"{q2m['workload']['sessions']} and {q2m['workload']['trials']}"
            )
        receipt["session_plan_sha256"] = run_order.order_sha256(plan)
        (run_dir / "session_plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
        records, verdicts, tokens, prev = [], [], [], None
        for cycle in range(len(plan)):
            if stop and stop[0]:
                receipt["stopped_before_cycle"] = cycle
                break
            record = driver.run_cycle(
                q2m, job_id, cycle, prev, run_dir, str(source_dir), cpus, session=plan[cycle]
            )
            record["step0_screenshots"] = keep_screenshots(cycles_dir, cycle)
            verdict = driver.cycle_verdict(record, tokens)
            records.append(record)
            verdicts.append(verdict)
            tokens.append(record["token"])
            prev = record["token"]
            (cycles_dir / f"record-{cycle:02d}.json").write_text(
                json.dumps(record, indent=2, sort_keys=True), encoding="utf-8"
            )
            print(json.dumps({"cycle_verdict": verdict}, sort_keys=True), flush=True)
        receipt["qcow2_sha256_after"] = driver.sha256_file(qcow2["host_path"])
        receipt["qcow2_unchanged"] = receipt["qcow2_sha256_after"] == receipt["qcow2_sha256_before"]
        receipt["labelled_containers_left"] = D.docker(
            "ps", "-a", "--filter", f"label=cotcodec.slurm_job={job_id}", "--format", "{{.Names}}"
        ).stdout.split()
        dangling = driver.run(
            [driver.DOCKER, "volume", "ls", "-q", "--filter", "dangling=true"], timeout=60
        )
        receipt["dangling_volumes_after"] = len(dangling.stdout.split())
        receipt["host_end"] = driver.snapshot_host(job_id)
        summary = driver.summarize(verdicts, records)
        summary["sessions"] = driver.session_summary(records)
        # driver.main's rule for session workloads (cold boots and isolation)
        summary["infra_gates_pass"] = (
            summary["boots_ok"] == summary["cycles"] == len(plan)
            and summary["no_gpu_all"]
            and summary["no_published_ports_all"]
            and summary["containers_removed_all"]
            and not summary["leaked_volumes"]
            and receipt["qcow2_unchanged"]
            and not receipt["labelled_containers_left"]
            and not summary["sessions"]["runner_errors"]
        )
        receipt["summary"] = summary
        receipt["verdicts"] = verdicts
        rc = 0 if summary["infra_gates_pass"] else 3
    except (Step0Error, driver.DriverError, OSError, ValueError) as exc:
        receipt["error"] = str(exc)[:500]
    receipt["finished_at"] = time.time()
    (run_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True))
    ids = D.docker("ps", "-aq", "--filter", f"label=cotcodec.slurm_job={job_id}").stdout.split()
    if ids:
        D.docker("rm", "--force", "--volumes", *ids, timeout=120)
    with (run_dir / "preflight.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"driver_exit={rc} labelled_containers_left={D.labelled_left(job_id)}\n")
    return rc


def run(m: Mapping[str, Any], run_dir: Path, source_dir: Path, job_id: str) -> dict[str, Any]:
    """Every campaign in order; USR1 ends the job after the current session."""
    from harness.q2.vm.manifest import source_tree_sha256

    tree = source_tree_sha256(str(source_dir))
    for item in m["campaigns"]:
        source = item["manifest"]["source"]
        _require(
            source["host_dir"] == str(source_dir.resolve()) and source["tree_sha256"] == tree,
            f"{item['manifest']['campaign_id']}: source is not this export",
        )
    stop = [False]
    signal.signal(signal.SIGUSR1, lambda *_: stop.__setitem__(0, True))
    out: dict[str, Any] = {
        "schema": "s2v5-step0-receipt-v1",
        "job_id": job_id,
        "check": CHECK,
        "purpose": m["purpose"],
        "campaigns": [],
        "t_start": time.time(),
    }
    for k, item in enumerate(m["campaigns"]):
        cid = item["manifest"]["campaign_id"]
        if stop[0]:
            out["campaigns"].append({"campaign_id": cid, "status": "not_started"})
            continue
        sub = run_dir / f"{k:02d}-{cid}"
        rc = run_canary(item, sub, source_dir, job_id, stop)
        (sub / "apdelta.json").write_text(json.dumps({"check": CHECK, "cells": item["cells"]}))
        out["campaigns"].append(
            {"campaign_id": cid, "dir": sub.name, "cells": item["cells"], "driver_exit": rc}
        )
    out["t_end"] = time.time()
    sha = source_dir / ".git_sha"
    out["executor_commit"] = sha.read_text().strip() if sha.is_file() else None
    (run_dir / "step0-receipt.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    return out


# --------------------------------------------------------------------------- submit (host)


def sbatch_argv(m: Mapping[str, Any], env: Mapping[str, str], batch: Path) -> list[str]:
    request = check_slurm(m)
    hours, mins = divmod(request["minutes"], 60)
    return [
        "sbatch",
        "--parsable",
        f"--cpus-per-task={request['cpus']}",
        f"--mem={request['memory_gb']}G",
        f"--time={hours:02d}:{mins:02d}:00",
        f"--job-name=s2v5-{m['name']}"[:60],
        "--export=ALL," + ",".join(f"{k}={v}" for k, v in env.items()),
        str(batch),
    ]


def check_cpu_only(argv: list[str], batch_text: str) -> None:
    """The request names no GPU and the batch file asks for none and refuses one."""
    joined = " ".join(argv).lower()
    _require(not any(w in joined for w in ("--gres", "--gpus", "gpu:")), "sbatch asks for a GPU")
    directives = [x for x in batch_text.splitlines() if x.startswith("#SBATCH")]
    _require(
        not any(("gres" in x.lower() or "gpu" in x.lower()) for x in directives),
        "the batch file asks for a GPU",
    )
    _require("refusing to start VMs" in batch_text, "the batch file lacks the GPU refusal")


def submit(
    manifest_path: Path, source_dir: Path, dry_run: bool, must_end_before: str | None
) -> dict[str, Any]:
    from harness.q2_stage1 import lane as s1a

    m = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), source_dir)
    request = check_slurm(m)
    text = L.canonical(m)
    digest = hashlib.sha256(text.encode()).hexdigest()
    run_root = Path(m["run_root"])
    stored = run_root / "manifests" / f"{digest}.json"
    batch = source_dir / BATCH
    env = {
        "COTCODEC_S2V5_MANIFEST_PATH_HEX": str(stored).encode().hex(),
        "COTCODEC_S2V5_MANIFEST_SHA256": digest,
        "COTCODEC_BATCH_SHA256": s1a.sha256_file(batch),
        "COTCODEC_SOURCE_HOST_HEX": str(source_dir.resolve()).encode().hex(),
        "COTCODEC_SOURCE_TREE_SHA256": s1a.tree_sha256(source_dir),
        "COTCODEC_RUN_ROOT_HEX": str(run_root).encode().hex(),
    }
    argv = sbatch_argv(m, env, batch)
    check_cpu_only(argv, batch.read_text(encoding="utf-8"))
    out: dict[str, Any] = {"manifest_sha256": digest, "manifest": str(stored), "argv": argv}
    out.update(request)
    if dry_run:
        return out
    # Scheduling (D85, D86, D94): an empty queue, and the job's limit ends before the next
    # successor-E session can start (the operator passes E4's earliest start).
    _require(must_end_before is not None, "--must-end-before is required to submit")
    deadline = datetime.fromisoformat(str(must_end_before).replace("Z", "+00:00"))
    # timezone.utc, not datetime.UTC: the host's python3 is 3.10
    ends = datetime.now(timezone.utc).timestamp() + 60 * request["minutes"]  # noqa: UP017
    _require(ends < deadline.timestamp(), f"the job's limit would end after {must_end_before}")
    queue = subprocess.run(
        ["squeue", "-h", "-o", "%i"], capture_output=True, text=True, timeout=60, check=True
    ).stdout.split()
    _require(not queue, f"the queue is not empty ({len(queue)} jobs)")
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_text(text, encoding="utf-8")
    done = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=True)
    out["job_id"] = done.stdout.strip()
    return out


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rd = sub.add_parser("render", help="step 0's manifest (Mac; PyYAML)")
    rd.add_argument("--source-dir", type=Path, required=True, help="export of the step-0 commit")
    rd.add_argument("--git-sha", required=True)
    rd.add_argument("--host-root", default=HOST_ROOT)
    rd.add_argument("--images-root", default=IMAGES_ROOT)
    rd.add_argument("--out", type=Path, required=True)
    v = sub.add_parser("validate")
    v.add_argument("manifest", type=Path)
    v.add_argument("--source-dir", type=Path, default=Path("."))
    s = sub.add_parser("submit")
    s.add_argument("manifest", type=Path)
    s.add_argument("--source-dir", type=Path, default=Path("."))
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--must-end-before", help="E4's earliest start, ISO 8601 UTC")
    r = sub.add_parser("run")
    r.add_argument("--manifest", type=Path, required=True)
    r.add_argument("--run-dir", type=Path, required=True)
    r.add_argument("--source-dir", type=Path, required=True)
    r.add_argument("--job-id", required=True)
    args = parser.parse_args(argv)
    if args.command == "render":
        m = render(args)
        args.out.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
        print(json.dumps({"campaigns": len(m["campaigns"]), **check_slurm(m)}))
        return 0
    if args.command == "validate":
        m = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
        print(json.dumps({"ok": True, "campaigns": len(m["campaigns"]), **check_slurm(m)}))
        return 0
    if args.command == "submit":
        out = submit(args.manifest, args.source_dir, args.dry_run, args.must_end_before)
        print(json.dumps(out, indent=1))
        return 0
    if not re.fullmatch(r"[1-9][0-9]{0,19}", args.job_id):
        raise SystemExit("job id must be numeric")
    m = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
    out = run(m, args.run_dir, args.source_dir, args.job_id)
    print(json.dumps({"campaigns": [(c["campaign_id"], c.get("driver_exit"))
                                    for c in out["campaigns"]]}))  # fmt: skip
    return 0 if all(c.get("driver_exit") == 0 for c in out["campaigns"]) else 3


if __name__ == "__main__":
    raise SystemExit(main())
