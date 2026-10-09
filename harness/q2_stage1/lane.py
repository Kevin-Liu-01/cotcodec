"""The S1a VM lane: the host side of a CPU-only VM job (registration sections 5.5-5.7, 7, 14).

Run by ``infra/slurm/host-single-node/s1a-vm.sbatch`` as a bare host process (standard
library only, D12). For each slot it boots a fresh VM container from the read-only qcow2
(the action-path suite's VM settings and ``docker run`` arguments,
``harness.q2.vm.driver.vm_run_argv``), starts one GPU-less episode container in that VM's
``--network none`` namespace (D13), waits for its record, and tears the VM down:

* the episode container is the checker-mutation study's metric image (OSWorld's locked
  environment) running ``harness.q2_stage1.driver`` as the host user, read-only root, no
  capabilities, no GPU variables; it mounts the source tree, the OSWorld tree and the
  pinned file cache read-only, the engine bridge's directory read-only and its own output
  directory read-write;
* **continuous dispatch** (section 5.6): ``V`` workers each take the next queued slot as
  soon as their previous VM is gone; a block is queued only after every slot of the
  previous block has been dispatched;
* **re-queue** (section 7.2): a slot lost to infrastructure on attempt 1 is queued once
  more, at the end of its block (or next, if its block is fully dispatched); a second loss
  leaves it missing;
* **stop** (section 14): on USR1 to the lane, or when the engine bridge writes ``usr1.json``
  (the GPU job's USR1), nothing new is dispatched; episodes in flight are cut and recorded
  ``cap_truncated``, and every slot never dispatched is recorded ``cap_truncated`` too;
* **fill rule** (section 5.6, session-1 A1 jobs only): extension blocks are queued after the
  base only while ``plan.fill_allowed`` holds; it reads the job's cost, never an outcome;
* **host snapshots** (section 5.5) at the start, before every block and at the end.

``validate_manifest`` keeps the lane inside the registration: the VM settings are the
action-path v2 runtime, the fake engine is for development only, a setup check runs no
model and no checker, and before the freeze no episode may touch a confirm task (G0 item 5's
setup-only check is the sole confirm contact, section 3.2).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA = "q2-stage1a-lane-v1"
EXPERIMENT_ID = "q2-stage1-rescoped-v1"
PURPOSES = ("development", "setup-check", "a0a", "a0b", "anc", "a1")
PRE_FREEZE_PURPOSES = ("development", "setup-check", "a0a", "a0b")
DEV_ONLY_PURPOSES = ("development", "a0a", "a0b")
# Registered model jobs (the anchor's are refused while it is UNAVAILABLE): their episode
# image, re-queue rule and episode timeout are the registration's, never a manifest's.
REGISTERED_PURPOSES = ("a0a", "a1")
# Section 4, "Episode container": the checker-mutation study's metric image (Pillow does the
# harness clients' screenshot resizing, so the image is part of the measurement).
EPISODE_IMAGE_ID = "sha256:2006c1a9247e4911a82508cd22e9d9a7efc5c13e35a20e8a03baac7112876230"
EPISODE_TIMEOUT_S = 3600.0
FIXED_KEYS = ("requeue", "episode_timeout_s", "episode_python")
# Slurm accounting is off on the host and scontrol forgets a finished job within minutes, so
# the lane records the GPU job's end itself: after vm.done it polls scontrol this long for a
# final state (the GPU job ends once its bridge stops).
GPU_END_WAIT_S = 180.0
GPU_FINAL_STATES = ("COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY")
OSWORLD_COMMIT = "b138d348256078fa634fc3b73567a7337c793e6b"
SPLITS = "program/evidence/q2-mutation/splits.json"
LEDGER = "program/preregistrations/ledger.jsonl"
REGISTRATION = "program/preregistrations/q2-stage1-rescoped-v1.md"
# Action-path v2 section 2.1 (the runtime S1a inherits; registration section 4).
VM_PINS = {
    "image": "happysixd/osworld-docker@sha256:"
    "0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9",
    "image_id": "sha256:fe8d9a5e5ad6c593d059887ea2c790481b3f32dd42fa961f2441cdbbe2c70cf4",
    "ram_size": "4G",
    "cpu_cores": 4,
    "disk_size": "32G",
    "memory_gb": 6,
    "network": "none-netns",
    "server_port": 5000,
}
QCOW2_SHA256 = "6bf667a852b3c307f61d9f09c42559351f45e0607e428b4997becf534cf4d313"
QCOW2_BYTES = 24_460_197_888
SETTLE_AFTER_RESET_S = 60.0
SETTLE_BEFORE_EVAL_S = 20.0
STEP_CAP = 15
SLOT_FIELDS = ("slot", "job", "size", "session", "task_id", "harness", "rerun", "block")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")
RUN_ROOT = "/home/kevin/cotcodec-runs/"


class LaneError(ValueError):
    """The manifest or a host input is outside the registration; nothing may start."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LaneError(message)


def frozen(source_dir: Path) -> bool:
    ledger = source_dir / LEDGER
    if not ledger.is_file():
        return False
    return any(
        json.loads(line).get("experiment_id") == EXPERIMENT_ID
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def task_sets(source_dir: Path) -> dict[str, set[str]]:
    from harness.q2_stage1.plan import task_pool

    splits = json.loads((source_dir / SPLITS).read_text(encoding="utf-8"))
    return {"dev": set(splits["dev"]), "pool": set(task_pool(splits["confirm"]))}


def validate_manifest(raw: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    """The lane's manifest, checked against the registration (raises ``LaneError``)."""
    m = json.loads(json.dumps(raw))
    _require(m.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    _require(m.get("experiment_id") == EXPERIMENT_ID, f"experiment_id must be {EXPERIMENT_ID}")
    purpose = m.get("purpose")
    _require(purpose in PURPOSES, f"purpose must be one of {PURPOSES}")
    _require(isinstance(m.get("name"), str) and SAFE.fullmatch(m["name"]), "unsafe name")
    is_frozen = frozen(source_dir)
    _require(
        purpose in PRE_FREEZE_PURPOSES or is_frozen,
        f"{purpose} runs only after the freeze (no ledger row for {EXPERIMENT_ID})",
    )
    vm = m.get("vm") or {}
    for key, value in VM_PINS.items():
        _require(vm.get(key) == value, f"vm.{key} must be {value!r} (action-path v2 2.1)")
    qcow2 = vm.get("qcow2") or {}
    _require(qcow2.get("sha256") == QCOW2_SHA256, "vm.qcow2.sha256 is not the pinned guest disk")
    _require(qcow2.get("size_bytes") == QCOW2_BYTES, "vm.qcow2.size_bytes differs")
    _require(str(qcow2.get("host_path", "")).startswith(RUN_ROOT), "qcow2 outside the run root")
    _require(isinstance(vm.get("guest_ip"), str), "vm.guest_ip is required")
    v = vm.get("concurrency")
    _require(isinstance(v, int) and 1 <= v <= 40, "vm.concurrency must be 1-40")
    _require(bool(IMAGE_ID.fullmatch(str(m.get("episode_image_id")))), "episode_image_id")
    osworld = m.get("osworld") or {}
    _require(osworld.get("commit") == OSWORLD_COMMIT, f"osworld.commit must be {OSWORLD_COMMIT}")
    for key in ("host_dir",):
        _require(str(osworld.get(key, "")).startswith(RUN_ROOT), f"osworld.{key} outside root")
    _require(str((m.get("file_cache") or {}).get("host_dir", "")).startswith(RUN_ROOT),
             "file_cache.host_dir outside the run root")  # fmt: skip
    mode = m.get("mode")
    engine = m.get("engine") or {}
    if purpose in REGISTERED_PURPOSES:
        _require(m.get("episode_image_id") == EPISODE_IMAGE_ID,
                 f"episode_image_id must be the registered metric image {EPISODE_IMAGE_ID} "
                 "(section 4)")  # fmt: skip
        for key in FIXED_KEYS:
            _require(key not in m, f"{key} is fixed for a registered job (sections 7.2, 14)")
        _require("{gpu_job_id}" in str(engine.get("bridge_dir", "")),
                 "a registered job names its GPU job through bridge_dir's {gpu_job_id} "
                 "(the lane checks that job's engine and limit)")  # fmt: skip
    _require(purpose == "setup-check" or "postconfig_probe" not in m,
             "postconfig_probe belongs to a setup check (G0 item 5)")  # fmt: skip
    if purpose == "setup-check":
        _require(mode == "setup-only", "a setup check runs mode setup-only")
        _require(engine.get("kind") == "none", "a setup check runs no engine")
        _require(isinstance(m.get("postconfig_probe", False), bool), "postconfig_probe: bool")
    else:
        _require(mode == "episode", "this purpose runs mode episode")
        _require(engine.get("kind") in ("fake", "bridge"), "engine.kind must be fake or bridge")
        if engine["kind"] == "fake":
            _require(purpose == "development", "the fake engine is for development only")
            _require(isinstance(engine.get("script"), dict), "engine.script is required")
        else:
            _require(str(engine.get("bridge_dir", "")).startswith(RUN_ROOT), "bridge_dir")
            _require(isinstance(engine.get("gpu_cap_min"), int), "engine.gpu_cap_min")
            if "{gpu_job_id}" in str(engine["bridge_dir"]):
                _require(str(engine.get("gpu_job_id_file", "")).startswith(RUN_ROOT),
                         "engine.gpu_job_id_file is required with {gpu_job_id}")  # fmt: skip
    from harness.q2_stage1.plan import PINNED_DATE_PURPOSES, PROMPT_DATE

    if purpose in PINNED_DATE_PURPOSES:
        pinned = f"date must be the pinned prompt date {PROMPT_DATE} (plan.PROMPT_DATE)"
        _require(m.get("date") == PROMPT_DATE, pinned)
    elif m.get("date") is not None:
        _require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(m["date"]))), "date: YYYY-MM-DD")
    _require(m.get("step_cap", STEP_CAP) == STEP_CAP, "step_cap is 15 (section 5.3)")
    _require(m.get("settle_after_reset_s", 60) == SETTLE_AFTER_RESET_S, "settle after reset 60 s")
    _require(m.get("settle_before_eval_s", 20) == SETTLE_BEFORE_EVAL_S, "settle before eval 20 s")
    sets = task_sets(source_dir)
    slots = m.get("slots") or []
    _require(bool(slots), "no slots")
    seen = set()
    for slot in slots:
        for key in SLOT_FIELDS:
            _require(key in slot, f"slot lacks {key}")
        _require(bool(SAFE.fullmatch(str(slot["slot"]))), f"unsafe slot id {slot['slot']}")
        _require(slot["slot"] not in seen, f"duplicate slot {slot['slot']}")
        seen.add(slot["slot"])
        task = slot["task_id"]
        if purpose == "setup-check":
            _require(task in sets["dev"] | sets["pool"], f"{task} is not a pool or dev task")
        elif not is_frozen or purpose in DEV_ONLY_PURPOSES:
            _require(task in sets["dev"], f"{task} is not a dev-split task (section 3.2)")
        else:
            _require(task in sets["pool"], f"{task} is outside the pool")
    fill = m.get("fill")
    if fill is not None:
        _require(purpose == "a1", "only an A1 job fills")
        _require(isinstance(fill.get("blocks"), list), "fill.blocks")
    check_plan_slots(m, source_dir)
    return m


def check_plan_slots(m: Mapping[str, Any], source_dir: Path) -> None:
    """A registered job's slots (and fill blocks) are the plan's, rendered by
    ``plan.a0a_slots`` and ``plan.a1_slots`` (raises ``LaneError``).

    A0a: the manifest names N* (the accepted attempt's ladder value); V is A1's, the dev
    tasks follow the committed setup-check records (G0 item 5). A1: the manifest names the
    frozen plan file in the source tree and its digest, which the registration must state
    as the frozen plan; a session-2 job names both session-1 jobs' record files, from which
    the extension blocks it runs are recomputed. The anchor (A0b, ANC) is UNAVAILABLE and
    has no runner, so those purposes are refused.
    """
    from harness.q2_stage1 import plan as P

    purpose, engine = m["purpose"], m.get("engine") or {}
    _require(purpose not in ("a0b", "anc"),
             "the anchor is UNAVAILABLE (G0 item 9.6) and no anchor runner is built")  # fmt: skip
    if purpose == "a0a":
        n_star = m.get("n_star")
        _require(isinstance(n_star, int) and not isinstance(n_star, bool), "n_star is required")
        v = P.a1_concurrency(n_star)
        _require(v is not None, "N* < 16: S1a does not start (G0 item 1)")
        _require(n_star >= P.A0A_MIN_NSTAR,
                 "N* = 16: K_base 32 is out of reach at V = 16, so the draft goes back to "
                 "review before A0a (section 5.5)")  # fmt: skip
        _require(m["vm"]["concurrency"] == v, f"A0a runs one wave at A1's V = {v}")
        _require(engine.get("gpu_cap_min") == P.CAP_MINUTES["A0a"], "A0a's GPU cap is 25")
        splits = json.loads((source_dir / SPLITS).read_text(encoding="utf-8"))
        try:
            rows = P.load_setup_check(source_dir)  # the registered records, by SHA-256
        except P.PlanError as exc:
            raise LaneError(str(exc)) from exc
        expected = P.a0a_slots(splits["dev"], P.dev_setup_ok(rows), v)
        _require(m["slots"] == expected, "A0a's slots differ from plan.a0a_slots")
        _require(m.get("fill") is None, "A0a does not fill")
        return
    if purpose != "a1":
        return
    plan = load_frozen_plan(m, source_dir)
    constants = plan["constants"]
    a1 = m.get("a1") or {}
    size, session = a1.get("size"), a1.get("session")
    _require(m["vm"]["concurrency"] == constants["a1_v"], f"A1 runs at V = {constants['a1_v']}")
    cap = constants["a1_cap_min"]
    _require(engine.get("gpu_cap_min") == cap, f"A1's GPU cap is T_A1 = {cap}")
    _require(size in P.SIZES and session in ("S1", "S2"), "a1.size and a1.session")
    prior = check_prior_jobs(a1, plan, P.a1_job(size, session))
    s2_blocks = None
    if session == "S2":
        s2_blocks = session_two_blocks(a1, plan, prior)
    try:
        slots, fill = P.a1_slots(plan, size, session, s2_blocks)
    except P.PlanError as exc:
        raise LaneError(str(exc)) from exc
    _require(m["slots"] == slots, f"A1 {size} {session}: slots differ from plan.a1_slots")
    _require(m.get("fill") == fill, f"A1 {size} {session}: fill differs from plan.a1_slots")


def load_frozen_plan(m: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    from harness.q2_stage1 import plan as P

    ref = m.get("plan") or {}
    path, sha = ref.get("path"), ref.get("sha256")
    _require(isinstance(path, str) and not path.startswith("/") and ".." not in Path(path).parts,
             "plan.path must name the plan file inside the source tree")  # fmt: skip
    _require(isinstance(sha, str) and bool(HEX64.fullmatch(sha)), "plan.sha256")
    data = json.loads((source_dir / path).read_text(encoding="utf-8"))
    body = {k: v for k, v in data.items() if k != "plan_sha256"}
    _require(data.get("plan_sha256") == P.digest(body) == sha,
             "the plan file does not match its digest")  # fmt: skip
    _require(data.get("status") == "frozen-constants", "A1 runs from the frozen plan")
    text = (source_dir / REGISTRATION).read_text(encoding="utf-8")
    _require(f"Frozen plan SHA-256: `{sha}`" in text,
             "the registration does not name this plan as the frozen plan")  # fmt: skip
    return data


PriorJobs = dict[str, tuple[list[dict[str, Any]], dict[str, Any]]]


def check_prior_jobs(a1: Mapping[str, Any], plan: Mapping[str, Any], job: str) -> PriorJobs:
    """Every earlier A1 job, in the registered order (``plan.a1_job_order``: 9B then 4B,
    session 1 then session 2), must be named with its lane record file and receipt by
    SHA-256, and none may have fired DR0 (section 11: when it fires, no further job starts).
    Returns each earlier job's (records, receipt)."""
    from harness.q2_stage1 import plan as P
    from harness.q2_stage1 import rules

    order = P.a1_job_order()
    earlier = order[: order.index(job)]
    items = a1.get("prior_jobs")
    _require(isinstance(items, list), "a1.prior_jobs lists the earlier A1 jobs (may be empty)")
    named = [item.get("job") for item in items]
    _require(named == earlier, f"a1.prior_jobs must be {earlier}, the A1 jobs before {job} "
                               "in the registered order")  # fmt: skip
    out: PriorJobs = {}
    for item in items:
        loaded = []
        for key in ("records", "receipt"):
            ref = item.get(key) or {}
            path = Path(str(ref.get("path", "")))
            _require(str(path).startswith(RUN_ROOT), f"{item['job']} {key} outside the run root")
            _require(path.is_file() and sha256_file(path) == ref.get("sha256"),
                     f"{path} does not match its digest")  # fmt: skip
            loaded.append(path.read_text(encoding="utf-8"))
        rows = [json.loads(x) for x in loaded[0].splitlines() if x.strip()]
        _require(bool(rows) and all(r.get("job") == item["job"] for r in rows),
                 f"{item['job']}'s record file must hold that job's records only")  # fmt: skip
        receipt = json.loads(loaded[1])
        _, size, session = item["job"].split("-")
        verdict = rules.job_dr0(rows, job=item["job"], size=size, session=session,
                                base=plan["base"], receipt=receipt)  # fmt: skip
        reasons = "; ".join(verdict["reasons"])
        fired = f"DR0 fired for {item['job']} ({reasons}): no further job starts (section 11)"
        _require(not verdict["fires"], fired)
        _require(
            isinstance(receipt.get("t_end"), int | float), f"{item['job']}'s receipt has no t_end"
        )
        out[item["job"]] = (rows, receipt)
    return out


def session_two_blocks(a1: Mapping[str, Any], plan: Mapping[str, Any], prior: PriorJobs) -> list:
    """The extension blocks both session-1 jobs completed (section 5.6), recomputed from
    their record files (``a1.prior_jobs``); the manifest must declare the same list."""
    from harness.q2_stage1 import plan as P
    from harness.q2_stage1.records import completed_extension_blocks

    jobs = [P.a1_job(size, "S1") for size in P.size_order()]
    s1 = [r for job in jobs for r in prior[job][0]]
    planned = {int(k): v for k, v in plan["extension_blocks"].items()}
    blocks = completed_extension_blocks(s1, planned, sessions=("S1",))
    declared = f"s2_extension_blocks must be {blocks}, the blocks both S1 jobs completed"
    _require(a1.get("s2_extension_blocks") == blocks, declared)
    return blocks


def earliest_start(m: Mapping[str, Any]) -> float | None:
    """A session-2 A1 job starts at least 12 hours after the later session-1 job ends
    (section 5.5): the later of each S1 pair's ends (the lane's ``t_end`` and its GPU job's
    recorded EndTime), plus ``plan.S2_GAP_H``. The receipts are the ones
    ``check_prior_jobs`` verified by digest."""
    from harness.q2_stage1 import plan as P

    a1 = m.get("a1") or {}
    if m.get("purpose") != "a1" or a1.get("session") != "S2":
        return None
    ends = []
    for item in a1.get("prior_jobs") or []:
        if str(item.get("job", "")).endswith("-S1"):
            receipt = json.loads(Path(item["receipt"]["path"]).read_text(encoding="utf-8"))
            gpu_end = (receipt.get("gpu_job_end") or {}).get("end_epoch")
            ends.append(max(float(receipt["t_end"]), float(gpu_end or 0.0)))
    _require(len(ends) == len(P.SIZES), "a session-2 job needs both session-1 receipts")
    return max(ends) + P.S2_GAP_H * 3600


# --------------------------------------------------------------------------- queue


@dataclass
class Slot:
    data: dict[str, Any]
    attempt: int = 1

    @property
    def id(self) -> str:
        return str(self.data["slot"])

    @property
    def block(self) -> str:
        return str(self.data["block"])


class Dispatcher:
    """Blocks in order; a block opens when the previous one is fully dispatched."""

    def __init__(self, slots: Sequence[Mapping[str, Any]]):
        self.blocks: list[str] = []
        self.pending: dict[str, collections.deque[Slot]] = {}
        for raw in slots:
            block = str(raw["block"])
            if block not in self.pending:
                self.blocks.append(block)
                self.pending[block] = collections.deque()
            self.pending[block].append(Slot(dict(raw)))
        self.current = 0
        self.lock = threading.Lock()
        self.dispatched: list[str] = []

    def add_block(self, block: str, slots: Sequence[Mapping[str, Any]]) -> None:
        with self.lock:
            self.blocks.append(block)
            self.pending[block] = collections.deque(Slot(dict(s)) for s in slots)

    def next(self) -> Slot | None:
        with self.lock:
            while self.current < len(self.blocks):
                queue = self.pending[self.blocks[self.current]]
                if queue:
                    slot = queue.popleft()
                    self.dispatched.append(f"{slot.id}#{slot.attempt}")
                    return slot
                self.current += 1
            return None

    def requeue(self, slot: Slot) -> None:
        """Attempt 2 at the end of its block, or next if its block is fully dispatched."""
        with self.lock:
            again = Slot(slot.data, attempt=2)
            index = self.blocks.index(slot.block)
            if index >= self.current and self.pending[slot.block]:
                self.pending[slot.block].append(again)
            elif self.current < len(self.blocks):
                self.pending[self.blocks[self.current]].appendleft(again)
            else:
                self.blocks.append(f"{slot.block}:requeue")
                self.pending[self.blocks[-1]] = collections.deque([again])

    def has_pending(self) -> bool:
        with self.lock:
            return any(self.pending[b] for b in self.blocks)

    def base_exhausted(self, base_blocks: set[str]) -> bool:
        with self.lock:
            return all(not self.pending[b] for b in base_blocks if b in self.pending)

    def remaining(self) -> list[Slot]:
        with self.lock:
            out = []
            for block in self.blocks:
                out.extend(self.pending[block])
                self.pending[block].clear()
            return out


# --------------------------------------------------------------------------- docker


class DockerOps:
    """The few Docker operations the lane needs (a fake replaces it in tests)."""

    def run(self, argv: list[str], timeout: float) -> subprocess.CompletedProcess:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)

    def start_vm(self, argv: list[str]) -> None:
        completed = self.run(argv, 120)
        if completed.returncode != 0:
            raise RuntimeError(f"vm start failed: {completed.stderr[-300:]}")

    def run_episode(self, argv: list[str], name: str, timeout: float,
                    stop: threading.Event, log: Path) -> int | None:  # fmt: skip
        """Run the episode container to completion; None when it was stopped or timed out."""
        with log.open("ab") as handle:
            proc = subprocess.Popen(argv, stdout=handle, stderr=subprocess.STDOUT)
            deadline = time.time() + timeout
            while proc.poll() is None:
                if stop.is_set() or time.time() > deadline:
                    subprocess.run(["docker", "kill", name], capture_output=True, timeout=60)
                    proc.wait(60)
                    return None
                time.sleep(1.0)
        return proc.returncode

    def remove(self, name: str) -> dict[str, Any]:
        from harness.q2.vm.driver import remove_container

        return remove_container(name)


# --------------------------------------------------------------------------- lane


@dataclass
class LaneConfig:
    manifest: dict[str, Any]
    job_id: str
    run_dir: Path
    source_dir: Path
    uid: int = field(default_factory=os.getuid)
    gid: int = field(default_factory=os.getgid)


def episode_argv(cfg: LaneConfig, name: str, vm: str, out_dir: Path, engine_dir: Path | None,
                 cpuset: str | None) -> list[str]:  # fmt: skip
    m = cfg.manifest
    argv = [
        "docker", "run", "--rm", "--name", name,
        "--label", f"cotcodec.slurm_job={cfg.job_id}", "--label", "cotcodec.q2s1a=1",
        "--label", "cotcodec.role=episode",
        "--runtime", "runc", "--network", f"container:{vm}",
        "--user", f"{cfg.uid}:{cfg.gid}", "--read-only",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=2g", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--memory", "6g", "--pids-limit", "2048",
        "--env", "CUDA_VISIBLE_DEVICES=", "--env", "NVIDIA_VISIBLE_DEVICES=void",
        "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "HOME=/tmp/home",
        "--env", "MPLCONFIGDIR=/tmp/mpl", "--env", "XDG_CACHE_HOME=/tmp/cache",
        "--volume", f"{cfg.source_dir}:/src:ro",
        "--volume", f"{m['osworld']['host_dir']}:/inputs/OSWorld:ro",
        "--volume", f"{m['file_cache']['host_dir']}:/inputs/file_cache/files:ro",
        "--volume", f"{out_dir}:/out",
        "--workdir", "/src",
    ]  # fmt: skip
    if engine_dir is not None:
        argv += ["--volume", f"{engine_dir}:/engine:ro"]
    if cpuset:
        argv += ["--cpuset-cpus", cpuset]
    argv += [m["episode_image_id"], m.get("episode_python", "/opt/venv-lock/bin/python"),
             "-m", "harness.q2_stage1.driver", "--config", "/out/config.json"]  # fmt: skip
    return argv


def vm_manifest_view(cfg: LaneConfig) -> dict[str, Any]:
    """What ``harness.q2.vm.driver.vm_run_argv`` reads, from the lane manifest."""
    return {"campaign_id": f"q2s1a-{cfg.manifest['name']}", "vm": cfg.manifest["vm"]}


class Lane:
    def __init__(
        self,
        cfg: LaneConfig,
        *,
        docker: DockerOps | None = None,
        clock: Callable[[], float] = time.time,
        cpusets: Sequence[dict[str, Any]] | None = None,
        snapshot: Callable[[str], dict[str, Any]] | None = None,
        certified: Sequence[str] | None = None,
        slurm_job: Callable[[str], dict[str, Any]] | None = None,
    ):
        self.cfg = cfg
        self.slurm_job = slurm_job or slurm_job_info
        self.gpu_job_id: str | None = None
        self.gpu_job: dict[str, Any] | None = None
        self.gpu_job_end: dict[str, Any] | None = None
        self.engine_ready: dict[str, Any] | None = None
        self.m = cfg.manifest
        self.docker = docker or DockerOps()
        self.clock = clock
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.records: list[dict[str, Any]] = []
        self.cpusets = list(cpusets) if cpusets is not None else None
        self.snapshot = snapshot or (lambda job: {"t": self.clock()})
        self.certified = list(certified) if certified is not None else certified_keysyms()
        self.dispatcher = Dispatcher(self.m["slots"])
        self.base_blocks = set(self.dispatcher.blocks)
        self.engine_dir: Path | None = None
        self.engine_proc: subprocess.Popen | None = None
        self.usr1_epoch: float | None = None
        self.first_dispatch: float | None = None
        self.fill_log: list[dict[str, Any]] = []
        self.snapshots: list[dict[str, Any]] = []
        self.d12_violation: list[str] | None = None
        self.seen_blocks: set[str] = set()
        self.cycle = -1
        self.cycle_lock = threading.Lock()
        self.fill_lock = threading.Lock()
        (cfg.run_dir / "episodes").mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- engine
    def start_engine(self) -> None:
        engine = self.m["engine"]
        if engine["kind"] == "none":
            return
        if engine["kind"] == "fake":
            self.engine_dir = self.cfg.run_dir / "bridge"
            self.engine_dir.mkdir(exist_ok=True)
            script = self.engine_dir / "script.json"
            script.write_text(json.dumps(engine["script"]), encoding="utf-8")
            self.engine_proc = subprocess.Popen(
                [sys.executable, "-E", "-s", "-m", "harness.q2_stage1.fake_engine",
                 "--socket", str(self.engine_dir / "engine.sock"), "--script", str(script),
                 "--log", str(self.engine_dir / "requests.jsonl"),
                 "--stop-file", str(self.engine_dir / "vm.done")],
                cwd=self.cfg.source_dir,
            )  # fmt: skip
            self._wait_for(self.engine_dir / "engine.sock", 60)
            return
        self.engine_dir = self.resolve_bridge_dir(engine)
        ready = self.engine_dir / "ready.json"
        self._wait_for(ready, float(engine.get("ready_timeout_s", 1800)))
        status = json.loads(ready.read_text(encoding="utf-8"))
        self.engine_ready = {k: status.get(k) for k in ("t_start", "t_ready", "engine_argv_sha256")}
        if self.gpu_job_id is not None:
            try:
                self.gpu_job = {"job_id": self.gpu_job_id, **self.slurm_job(self.gpu_job_id)}
            except Exception as exc:  # noqa: BLE001 - a registered job refuses below
                self.gpu_job = {"job_id": self.gpu_job_id, "error": f"{exc}"[:300]}
        if self.m["purpose"] in REGISTERED_PURPOSES:
            self.check_registered_engine(status)
        # The GPU job's USR1 comes 180 s before its Slurm limit, counted from its Slurm start
        # (the bridge's own start is later, by the container's start-up).
        start = (self.gpu_job or {}).get("start_epoch")
        base = float(start) if isinstance(start, int | float) else float(status["t_start"])
        self.usr1_epoch = base + engine["gpu_cap_min"] * 60 - 180

    def wait_gpu_end(self, wait_s: float = GPU_END_WAIT_S, poll_s: float = 5.0) -> dict | None:
        """The GPU job's final ``scontrol`` state and EndTime, polled after vm.done (the
        realized-cost input of section 9 item 10); None when there is no GPU job or Slurm did
        not report a final state in time (the bridge's ``stopped.json`` then stands in)."""
        if self.gpu_job_id is None:
            return None
        end = time.monotonic() + wait_s
        while True:
            try:
                info = self.slurm_job(self.gpu_job_id)
            except Exception as exc:  # noqa: BLE001 - forgotten or unreachable: recorded
                return {"job_id": self.gpu_job_id, "error": f"{exc}"[:300]}
            if info.get("state") in GPU_FINAL_STATES:
                return {"job_id": self.gpu_job_id, **info}
            if time.monotonic() > end:
                # A running job's EndTime is its projected limit, not an end: dropped.
                seen = {k: v for k, v in info.items() if not k.startswith("end_")}
                return {"job_id": self.gpu_job_id, "error": "no final state", **seen}
            time.sleep(poll_s)

    def check_registered_engine(self, status: Mapping[str, Any]) -> None:
        """A0a and A1 dispatch only against the registered engine: the GPU job's argv is
        ``plan.engine_argv`` for this job's size (model and flags) and its Slurm time limit
        is the job's GPU cap, the minutes D22 counts (sections 4, 6.1)."""
        from harness.q2_stage1 import plan as P

        size = P.A0A_SIZE if self.m["purpose"] == "a0a" else (self.m.get("a1") or {}).get("size")
        expected = P.engine_argv(P.MODEL_DIRS[str(size)], P.SERVED_NAME)
        if status.get("engine_argv") != expected:
            raise LaneError(f"the GPU job's engine argv is not the registered {size} argv")
        info = self.gpu_job or {}
        cap = int(self.m["engine"]["gpu_cap_min"])
        if info.get("time_limit_min") != cap:
            raise LaneError(f"the GPU job's Slurm time limit is {info.get('time_limit_min')} "
                            f"minutes, not its cap of {cap} ({info.get('error', '')})")  # fmt: skip
        if not isinstance(info.get("start_epoch"), int | float):
            raise LaneError("the GPU job's Slurm start time is unknown")

    def resolve_bridge_dir(self, engine: Mapping[str, Any]) -> Path:
        """The GPU job's bridge directory. The VM job is submitted first, so the GPU job's id
        (its run directory) is not known then: ``bridge_dir`` may hold ``{gpu_job_id}``,
        read from ``gpu_job_id_file`` once the operator has submitted the GPU job."""
        template = str(engine["bridge_dir"])
        if "{gpu_job_id}" not in template:
            return Path(template)
        id_file = Path(engine["gpu_job_id_file"])
        self._wait_for(id_file, float(engine.get("ready_timeout_s", 1800)))
        job = id_file.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[1-9][0-9]{0,19}", job):
            raise LaneError(f"{id_file} does not hold a Slurm job id")
        self.gpu_job_id = job
        return Path(template.replace("{gpu_job_id}", job))

    def _wait_for(self, path: Path, seconds: float) -> None:
        end = self.clock() + seconds
        while not path.exists():
            if self.clock() > end or self.stop.is_set():
                raise RuntimeError(f"{path} did not appear within {seconds} s")
            time.sleep(0.5)

    def stop_engine(self) -> None:
        if self.engine_dir is not None and self.m["engine"]["kind"] in ("fake", "bridge"):
            (self.engine_dir / "vm.done").write_text(str(self.clock()), encoding="utf-8")
        if self.engine_proc is not None:
            try:
                self.engine_proc.wait(30)
            except subprocess.TimeoutExpired:
                self.engine_proc.kill()

    def engine_stopped(self) -> bool:
        return self.engine_dir is not None and (self.engine_dir / "usr1.json").exists()

    # ---------------------------------------------------------------- slots
    def episode_config(self, slot: Slot, out_dir: Path, t_vm_start: float) -> dict[str, Any]:
        data = slot.data
        return {
            "job": data["job"], "size": data["size"], "session": data["session"],
            "task_id": data["task_id"], "harness": data["harness"], "rerun": data["rerun"],
            "attempt": slot.attempt, "extension_block": data.get("extension_block"),
            "block": data["block"], "slot": slot.id, "out_dir": "/out",
            "guest_ip": self.m["vm"]["guest_ip"], "server_port": self.m["vm"]["server_port"],
            "osworld_dir": "/inputs/OSWorld", "file_cache_dir": "/inputs/file_cache/files",
            "engine_socket": "/engine/engine.sock", "mode": self.m["mode"],
            "certified_keysyms": self.certified, "t_vm_start": t_vm_start,
            "date": self.m.get("date"), **self.setup_check_config(data["task_id"]),
        }  # fmt: skip

    def setup_check_config(self, task_id: str) -> dict[str, Any]:
        """G0 item 5's second pass: the postconfig probe and the registered diagnostics."""
        if self.m["mode"] != "setup-only":
            return {}
        from harness.q2_stage1.plan import SETUP_DIAGNOSTICS

        return {
            "postconfig_probe": bool(self.m.get("postconfig_probe")),
            "diagnostics": [dict(d) for d in SETUP_DIAGNOSTICS.get(task_id, ())],
        }

    def run_slot(self, slot: Slot, worker: int, cycle: int) -> dict[str, Any]:
        from harness.q2.vm.driver import vm_name, vm_run_argv

        cpus = self.cpusets[worker] if self.cpusets else {"vm": None, "vm_mems": None,
                                                          "runner": None}  # fmt: skip
        name = vm_name(self.cfg.job_id, cycle)
        episode_name = f"cotcodec-q2s1a-{self.cfg.job_id}-e{cycle:03d}"
        out_dir = self.cfg.run_dir / "episodes" / f"{slot.id.replace(':', '_')}.a{slot.attempt}"
        out_dir.mkdir(parents=True, exist_ok=True)
        t_dispatch = self.clock()
        if self.first_dispatch is None:
            self.first_dispatch = t_dispatch
        host: dict[str, Any] = {"t_dispatch": t_dispatch, "vm": name, "worker": worker,
                                "cpus": cpus}  # fmt: skip
        record: dict[str, Any] | None = None
        started_vm = False
        try:
            argv = vm_run_argv(vm_manifest_view(self.cfg), self.cfg.job_id, cycle, cpus["vm"],
                               cpus["vm_mems"])  # fmt: skip
            t_vm = self.clock()
            try:
                started_vm = True
                self.docker.start_vm(argv)
            except Exception as exc:  # noqa: BLE001 - a VM that will not start is a boot loss
                record = self.loss(slot, "vm_boot", f"{exc}")
            if record is None:
                record = self.episode(slot, out_dir, t_vm, episode_name, name, cpus, host)
        except Exception as exc:  # noqa: BLE001 - a lane-side fault loses the slot, not the job
            record = self.loss(slot, "runner_crash", f"lane: {type(exc).__name__}: {exc}")
        finally:
            if started_vm:
                host["teardown"] = self.docker.remove(name)
            host["t_teardown"] = self.clock()
        return self.finish_slot(record, host, t_dispatch)

    def episode(self, slot: Slot, out_dir: Path, t_vm: float, episode_name: str, vm: str,
                cpus: Mapping[str, Any], host: dict[str, Any]) -> dict[str, Any]:  # fmt: skip
        config = self.episode_config(slot, out_dir, t_vm)
        (out_dir / "config.json").write_text(json.dumps(config, indent=1), encoding="utf-8")
        argv = episode_argv(self.cfg, episode_name, vm, out_dir, self.engine_dir, cpus["runner"])
        timeout = float(self.m.get("episode_timeout_s", EPISODE_TIMEOUT_S))
        rc = self.docker.run_episode(argv, episode_name, timeout, self.stop,
                                     out_dir / "container.log")  # fmt: skip
        host["episode_rc"] = rc
        path = out_dir / "episode.json"
        if rc is None:
            if self.stop.is_set():
                return self.truncated(slot, "cut at the stop signal")
            return self.loss(slot, "runner_crash", f"episode exceeded {timeout} s")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return self.loss(slot, "runner_crash", f"episode container exited {rc}")

    def base_record(self, slot: Slot) -> dict[str, Any]:
        from harness.q2_stage1.records import SCHEMA as EPISODE_SCHEMA

        d = slot.data
        return {
            "schema": EPISODE_SCHEMA, "job": d["job"], "size": d["size"],
            "session": d["session"], "task_id": d["task_id"], "harness": d["harness"],
            "rerun": d["rerun"], "extension_block": d.get("extension_block"),
            "attempt": slot.attempt, "block": d["block"], "slot": slot.id, "score": None,
            "steps": 0, "truncated_steps": 0, "truncated_no_tool_call_steps": 0, "ir_errors": 0,
            "uncertified_key_actions": 0, "context_fallbacks": 0,
        }  # fmt: skip

    def loss(self, slot: Slot, kind: str, detail: str) -> dict[str, Any]:
        status = "setup_failed" if self.m["mode"] == "setup-only" else "infrastructure"
        return {**self.base_record(slot), "status": status, "infrastructure_type": kind,
                "infrastructure_detail": detail[:500], "ended": "infra"}  # fmt: skip

    def truncated(self, slot: Slot, detail: str) -> dict[str, Any]:
        return {**self.base_record(slot), "status": "cap_truncated", "infrastructure_type": None,
                "cap_detail": detail}  # fmt: skip

    def finish_slot(self, record: dict[str, Any], host: dict[str, Any], t0: float) -> dict:
        if "t_teardown" in host:
            host["slot_occupancy_s"] = round(host["t_teardown"] - t0, 3)
        record["host"] = host
        with self.lock:
            self.records.append(record)
            with (self.cfg.run_dir / self.records_name()).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def records_name(self) -> str:
        return "setup.jsonl" if self.m["mode"] == "setup-only" else "episodes.jsonl"

    # ---------------------------------------------------------------- fill rule
    def maybe_fill(self) -> None:
        from harness.q2_stage1 import plan

        fill = self.m.get("fill")
        if not fill or not self.dispatcher.base_exhausted(self.base_blocks):
            return
        with self.fill_lock:
            self._fill(plan, fill)

    def _fill(self, plan: Any, fill: dict[str, Any]) -> None:
        if self.dispatcher.has_pending():
            return
        blocks = fill["blocks"]
        while blocks and self.usr1_epoch is not None:
            scored = [r for r in self.records if r.get("status") in ("scored", "infrastructure")]
            if not scored or self.first_dispatch is None:
                return
            c_job_h = (self.clock() - self.first_dispatch) / 3600 / len(scored)
            minutes = (self.usr1_epoch - self.clock()) / 60
            allowed = plan.fill_allowed(c_job_h, minutes, int(fill.get("block_episodes", 32)))
            self.fill_log.append({"t": self.clock(), "c_job_h": c_job_h,
                                  "minutes_to_usr1": minutes, "allowed": allowed,
                                  "block": blocks[0]["label"]})  # fmt: skip
            if not allowed:
                blocks.clear()
                return
            block = blocks.pop(0)
            for sub in block["sub_blocks"]:
                self.dispatcher.add_block(sub["label"], sub["slots"])
            return

    # ---------------------------------------------------------------- run
    def next_cycle(self) -> int:
        with self.cycle_lock:
            self.cycle += 1
            return self.cycle

    def worker(self, index: int) -> None:
        while not self.stop.is_set():
            if self.engine_stopped():
                self.stop.set()
                break
            self.maybe_fill()
            slot = self.dispatcher.next()
            if slot is None:
                break
            if slot.block not in self.seen_blocks:
                with self.lock:
                    if slot.block not in self.seen_blocks:
                        self.seen_blocks.add(slot.block)
                        self.snapshots.append(
                            {"block": slot.block, **self.snapshot(self.cfg.job_id)}
                        )
            try:
                record = self.run_slot(slot, index, self.next_cycle())
            except Exception as exc:  # noqa: BLE001 - the lane keeps going; the slot is lost
                record = self.finish_slot(
                    self.loss(slot, "runner_crash", f"lane: {type(exc).__name__}: {exc}"),
                    {"t_dispatch": self.clock()}, self.clock(),
                )  # fmt: skip
            if record.get("gpu_devices"):
                # D12: an episode container saw a GPU device; nothing more is dispatched.
                self.d12_violation = list(record["gpu_devices"])
                self.stop.set()
                break
            infra = record.get("status") in ("infrastructure", "setup_failed")
            if infra and slot.attempt == 1 and self.m.get("requeue", True):
                self.dispatcher.requeue(slot)

    def run(self) -> dict[str, Any]:
        started = self.clock()
        self.snapshots.append({"block": "start", **self.snapshot(self.cfg.job_id)})
        receipt: dict[str, Any] = {"schema": "q2-stage1a-lane-receipt-v1",
                                   "job_id": self.cfg.job_id, "name": self.m["name"],
                                   "purpose": self.m["purpose"], "t_start": started}  # fmt: skip
        try:
            not_before = earliest_start(self.m)
            if not_before is not None and self.clock() < not_before:
                raise LaneError(f"a session-2 job starts at least 12 h after the later "
                                f"session-1 job ends: not before {not_before:.0f}")  # fmt: skip
            self.start_engine()
            if self.m["mode"] == "episode" and not self.certified:
                raise LaneError("the certified keysym set is unavailable; exposure is required")
            workers = [
                threading.Thread(target=self.worker, args=(i,), daemon=True)
                for i in range(self.m["vm"]["concurrency"])
            ]
            for thread in workers:
                thread.start()
            for thread in workers:
                while thread.is_alive():
                    thread.join(1.0)
                    if self.engine_stopped():
                        self.stop.set()
        except Exception as exc:  # noqa: BLE001 - recorded in the receipt
            receipt["error"] = f"{type(exc).__name__}: {exc}"[:500]
            self.stop.set()
        finally:
            for slot in self.dispatcher.remaining():
                self.finish_slot(self.truncated(slot, "never dispatched"), {}, self.clock())
            self.stop_engine()
            self.snapshots.append({"block": "end", **self.snapshot(self.cfg.job_id)})
        if self.d12_violation:
            receipt["error"] = (
                f"D12: GPU device files visible in an episode container: {self.d12_violation}"[:500]
            )
        receipt.update(
            gpu_job=self.gpu_job, engine_ready=self.engine_ready,
            bridge_dir=str(self.engine_dir) if self.engine_dir is not None else None,
            first_dispatch=self.first_dispatch, usr1_epoch=self.usr1_epoch,
        )  # fmt: skip
        receipt.update(
            t_end=self.clock(), stopped=self.stop.is_set(), dispatched=self.dispatcher.dispatched,
            records=len(self.records), fill=self.fill_log, snapshots=self.snapshots,
            statuses=dict(collections.Counter(r.get("status") for r in self.records)),
        )  # fmt: skip
        self.write_receipt(receipt)
        # The GPU job's end comes after vm.done; the receipt is written first so a VM job
        # that reaches its own limit while waiting still leaves one (section 9 item 10).
        self.gpu_job_end = self.wait_gpu_end()
        if self.gpu_job_end is not None:
            receipt["gpu_job_end"] = self.gpu_job_end
            self.write_receipt(receipt)
        return receipt

    def write_receipt(self, receipt: Mapping[str, Any]) -> None:
        path = self.cfg.run_dir / "lane-receipt.json"
        tmp = path.with_name(f".{path.name}.tmp")
        tmp.write_text(json.dumps(receipt, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)


def parse_time_limit(value: str) -> int | None:
    """Slurm's ``TimeLimit`` ([days-]hours:minutes:seconds, minutes:seconds or minutes) in
    whole minutes; None for UNLIMITED or anything else."""
    match = re.fullmatch(r"(?:(\d+)-)?(\d+)(?::(\d+))?(?::(\d+))?", value.strip())
    if not match:
        return None
    days, a, b, c = match.groups()
    if c is not None:
        hours, minutes, seconds = int(a), int(b), int(c)
    elif b is not None:
        hours, minutes, seconds = (int(a), int(b), 0) if days else (0, int(a), int(b))
    else:
        hours, minutes, seconds = (int(a), 0, 0) if days else (0, int(a), 0)
    return int(days or 0) * 1440 + hours * 60 + minutes + (1 if seconds else 0)


def parse_scontrol(text: str) -> dict[str, Any]:
    """The fields the lane reads from ``scontrol show job -o``: state, Slurm start time (the
    host's local time, as an epoch) and time limit in minutes."""
    fields = dict(
        token.split("=", 1) for token in text.split() if "=" in token and not token.startswith("=")
    )
    out: dict[str, Any] = {"state": fields.get("JobState"), "time_limit_min": None,
                           "start_epoch": None}  # fmt: skip
    if fields.get("TimeLimit"):
        out["time_limit_min"] = parse_time_limit(fields["TimeLimit"])
    for key, name in (("start", "StartTime"), ("end", "EndTime")):
        value = fields.get(name, "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
            out[f"{key}_epoch"] = time.mktime(time.strptime(value, "%Y-%m-%dT%H:%M:%S"))
            out[f"{key}_time"] = value
    return out


def slurm_job_info(job_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[1-9][0-9]{0,19}", str(job_id)):
        raise LaneError("not a Slurm job id")
    done = subprocess.run(["scontrol", "show", "job", "-o", str(job_id)],
                          capture_output=True, text=True, timeout=60, check=True)  # fmt: skip
    return parse_scontrol(done.stdout)


def certified_keysyms() -> list[str]:
    try:
        from harness.q2_stage1.records import certified_keysym_set

        return sorted(certified_keysym_set())
    except Exception:  # noqa: BLE001 - recorded as unknown: exposure is then not counted
        return []


def plan_cpusets(allocated: Sequence[int], concurrency: int, cores: int) -> list[dict[str, Any]]:
    """One CPU set per VM (``cores`` each); the episode containers share the rest."""
    from harness.q2.vm.driver import format_cpuset

    pool = sorted(allocated)
    need = concurrency * cores
    if len(pool) < need + 1:
        raise LaneError(f"the allocation has {len(pool)} CPUs; {need} VM CPUs and 1 more needed")
    runner = format_cpuset(pool[need:])
    return [
        {"vm": format_cpuset(pool[i * cores : (i + 1) * cores]), "vm_mems": None, "runner": runner}
        for i in range(concurrency)
    ]


def tree_sha256(source_dir: Path) -> str:
    from harness.q2.vm.manifest import source_tree_sha256

    return source_tree_sha256(str(source_dir))


BATCH = "infra/slurm/host-single-node/s1a-vm.sbatch"
# A temporary host-load limit (e.g. 8 CPUs while the action-path v2 acceptance campaigns
# run) is an operator flag, never a registered rule: it applies to these purposes only.
HOST_LOAD_PURPOSES = ("development", "setup-check")


def canonical(manifest: Mapping[str, Any]) -> str:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_host(m: Mapping[str, Any]) -> dict[str, Any]:
    """Host inputs exist and match the manifest (run on the host before submitting)."""
    qcow2 = Path(m["vm"]["qcow2"]["host_path"])
    _require(qcow2.is_file() and not qcow2.is_symlink(), "qcow2 missing")
    _require(qcow2.stat().st_size == QCOW2_BYTES, "qcow2 size differs")
    _require(not qcow2.stat().st_mode & 0o222, "qcow2 must be read-only")
    for image in (m["vm"]["image_id"], m["episode_image_id"]):
        out = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image],
                             capture_output=True, text=True, timeout=60)  # fmt: skip
        _require(out.stdout.strip() == image, f"image {image} is not present")
    head = subprocess.run(["git", "-C", m["osworld"]["host_dir"], "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=60).stdout.strip()  # fmt: skip
    _require(head == OSWORLD_COMMIT, f"OSWorld checkout is at {head}")
    _require(Path(m["file_cache"]["host_dir"]).is_dir(), "file cache directory missing")
    return {"qcow2_bytes": QCOW2_BYTES, "osworld_head": head}


def check_slurm(m: Mapping[str, Any], host_load_cpus: int | None = None) -> dict[str, int]:
    """The VM job's Slurm request against section 5.5 (raises ``LaneError``).

    A registered job (A0a, A0b, ANC, A1) takes exactly ``plan.vm_job_cpus(V)`` CPUs (4V for
    the VMs plus ``runner_cpus(V)``: 90 at V = 20, 72 at V = 16), which must fit beside its
    GPU job (``plan.check_cpus``), and its limit is the GPU cap plus 10 minutes. A
    development or setup-check job needs the VMs' CPUs and one more; ``host_load_cpus``
    caps it (the operator's temporary host-load limit) and is refused for any other purpose.
    """
    from harness.q2_stage1 import plan

    slurm = m.get("slurm") or {}
    cpus, memory, minutes = slurm.get("cpus"), slurm.get("memory_gb"), slurm.get("minutes")
    v, cores, purpose = m["vm"]["concurrency"], m["vm"]["cpu_cores"], m["purpose"]
    _require(isinstance(cpus, int) and not isinstance(cpus, bool), "slurm.cpus must be an int")
    if host_load_cpus is not None:
        _require(purpose in HOST_LOAD_PURPOSES,
                 f"a host-load CPU limit applies to {HOST_LOAD_PURPOSES} only; a {purpose} "
                 "job takes section 5.5's CPUs")  # fmt: skip
        _require(isinstance(host_load_cpus, int) and host_load_cpus >= 1, "host-load limit")
    if purpose in HOST_LOAD_PURPOSES:
        fits = v * cores + 1 <= cpus <= plan.CPU_LIMIT
        _require(fits, f"slurm.cpus must fit {v} VMs and a runner CPU, within {plan.CPU_LIMIT}")
        if host_load_cpus is not None:
            above = f"slurm.cpus {cpus} is above the host-load limit {host_load_cpus}"
            _require(cpus <= host_load_cpus, above)
    else:
        need = plan.vm_job_cpus(v)
        _require(cpus == need, f"slurm.cpus must be 4V + runner_cpus(V) = {need} at V = {v} "
                               "(section 5.5)")  # fmt: skip
        try:
            plan.check_cpus([v], 1)
        except plan.PlanError as exc:
            raise LaneError(str(exc)) from exc
    _require(isinstance(memory, int) and memory >= 6 * v + 6, "slurm.memory_gb too small")
    _require(isinstance(minutes, int) and 1 <= minutes <= 720, "slurm.minutes 1-720")
    engine = m.get("engine") or {}
    if engine.get("kind") == "bridge":
        limit = int(engine["gpu_cap_min"]) + plan.VM_JOB_EXTRA_MIN
        _require(minutes == limit,
                 f"slurm.minutes must be the GPU cap plus {plan.VM_JOB_EXTRA_MIN} = {limit} "
                 "(sections 5.5, 14)")  # fmt: skip
    return {"cpus": cpus, "memory_gb": memory, "minutes": minutes}


def submit(
    manifest_path: Path, source_dir: Path, dry_run: bool, host_load_cpus: int | None = None
) -> dict[str, Any]:
    m = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), source_dir)
    request = check_slurm(m, host_load_cpus)
    cpus, memory, minutes = request["cpus"], request["memory_gb"], request["minutes"]
    host = check_host(m)
    text = canonical(m)
    digest = hashlib.sha256(text.encode()).hexdigest()
    run_root = Path(m["run_root"])
    _require(str(run_root).startswith(RUN_ROOT), "run_root outside the run root")
    stored = run_root / "manifests" / f"{digest}.json"
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_text(text, encoding="utf-8")
    batch = source_dir / BATCH
    env = {
        "COTCODEC_S1A_MANIFEST_PATH_HEX": str(stored).encode().hex(),
        "COTCODEC_S1A_MANIFEST_SHA256": digest,
        "COTCODEC_BATCH_SHA256": sha256_file(batch),
        "COTCODEC_SOURCE_HOST_HEX": str(source_dir.resolve()).encode().hex(),
        "COTCODEC_SOURCE_TREE_SHA256": tree_sha256(source_dir),
        "COTCODEC_RUN_ROOT_HEX": str(run_root).encode().hex(),
    }
    hours, mins = divmod(minutes, 60)
    argv = ["sbatch", "--parsable", f"--cpus-per-task={cpus}", f"--mem={memory}G",
            f"--time={hours:02d}:{mins:02d}:00", f"--job-name=s1a-{m['name']}"[:60]]  # fmt: skip
    not_before = earliest_start(m)
    if not_before is not None:
        # Slurm holds a session-2 VM job (and so its GPU job) until the 12 h gap has passed;
        # the lane checks the gap again before it starts the engine wait.
        begin = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(math.ceil(not_before)))
        argv.append(f"--begin={begin}")
    argv += ["--export=ALL," + ",".join(f"{k}={v}" for k, v in env.items()), str(batch)]
    out = {"manifest_sha256": digest, "manifest": str(stored), "host": host, "argv": argv}
    if not dry_run:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=True)
        out["job_id"] = done.stdout.strip()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a validated manifest (inside s1a-vm.sbatch)")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument("--source-dir", type=Path, required=True)
    run.add_argument("--job-id", required=True)
    check = sub.add_parser("validate", help="validate a manifest against a source tree")
    check.add_argument("manifest", type=Path)
    check.add_argument("--source-dir", type=Path, default=Path("."))
    sbatch = sub.add_parser("submit", help="validate, check the host and submit (on the host)")
    sbatch.add_argument("manifest", type=Path)
    sbatch.add_argument("--source-dir", type=Path, default=Path("."))
    sbatch.add_argument("--dry-run", action="store_true")
    sbatch.add_argument("--host-load-max-cpus", type=int, default=None,
                        help="temporary host-load CPU cap (development, setup-check)")  # fmt: skip
    args = parser.parse_args(argv)
    if args.command == "submit":
        out = submit(args.manifest, args.source_dir, args.dry_run, args.host_load_max_cpus)
        print(json.dumps(out, indent=1))
        return 0
    if args.command == "validate":
        manifest = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
        digest = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        print(json.dumps({"ok": True, "manifest_sha256": digest, "slots": len(manifest["slots"])}))
        return 0
    if not re.fullmatch(r"[1-9][0-9]{0,19}", args.job_id):
        raise SystemExit("job id must be numeric")
    manifest = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
    from harness.q2.vm.driver import slurm_cpu_ids, snapshot_host

    cpusets = plan_cpusets(slurm_cpu_ids(args.job_id), manifest["vm"]["concurrency"],
                           manifest["vm"]["cpu_cores"])  # fmt: skip
    lane = Lane(
        LaneConfig(manifest, args.job_id, args.run_dir, args.source_dir),
        cpusets=cpusets,
        snapshot=snapshot_host,
    )
    signal.signal(signal.SIGUSR1, lambda *_: lane.stop.set())
    receipt = lane.run()
    print(json.dumps({k: receipt[k] for k in ("records", "statuses", "stopped")}))
    return 0 if "error" not in receipt else 3


if __name__ == "__main__":
    raise SystemExit(main())
