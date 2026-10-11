"""The S2 v4 VM lane: S1a's lane with a per-slot cell image (registration P0.3, D76 (b)).

Run by ``infra/slurm/host-single-node/s2v4-vm.sbatch`` as a bare host process (standard library
only; the host's Python 3.10). It is the S1a lane (``harness.q2_stage1.lane.Lane``: continuous
dispatch, one re-queue of a slot lost to infrastructure, the stop signal, host snapshots, the
D12 stop) with one change, the per-slot overlay: each slot names a cell, and its VM container
mounts that cell's image read-only at ``/System.qcow2`` through the action-path v2 runtime's own
``docker run`` arguments (``harness.q2.vm.driver.vm_run_argv``) with only ``vm.qcow2`` replaced.
Everything else in the VM runtime (the OSWorld image digest, RAM, cores, disk size, network
namespace) is the certified one (D53). The episode container runs ``harness.s2_locale.vm_probe``.

Image pins: the stock cell S is the certified disk (``s1a.QCOW2_SHA256``); every other cell's
image is pinned in ``harness/s2_locale/images.json`` (written from the build record of
``image_build.py``). ``validate_manifest`` refuses an image whose digest or size differs from
the pins, and the job hashes every image it will mount before it dispatches any slot
(``verify_images``), so a slot always runs on the pinned bytes.

Purposes: before the registration is frozen only ``development`` runs, on dev-split tasks
(the registration's development smoke). Phase 0 proper's purposes are added with the freeze.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import signal
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_stage1 import lane as s1a

SCHEMA = "s2v4-vm-lane-v1"
EXPERIMENT_ID = "s2-arabic-cua-locale-v4"
REGISTRATION = "program/preregistrations/s2-arabic-cua-locale-v4.md"
LEDGER = "program/preregistrations/ledger.jsonl"
SPLITS = "program/evidence/q2-mutation/splits.json"
IMAGES = "harness/s2_locale/images.json"
PURPOSES = ("development",)
MODE = "s2v4-probe"
EPISODE_IMAGE_ID = s1a.EPISODE_IMAGE_ID
VM_PINS = dict(s1a.VM_PINS)  # action-path v2 section 2.1
OSWORLD_COMMIT = s1a.OSWORLD_COMMIT
RUN_ROOT = s1a.RUN_ROOT
MAX_CONCURRENCY = 32  # D53: certified at no more than 32 concurrent VMs
STOCK = {"cell": "S", "sha256": s1a.QCOW2_SHA256, "size_bytes": s1a.QCOW2_BYTES}
SLOT_FIELDS = ("slot", "task_id", "cell", "rep", "block")
KINDS = ("capture", "gold")  # vm_probe.py, vm_gold.py
FILE_CACHE_RECEIPTS = "program/evidence/q2-mutation/harness/file-cache-receipts.tsv"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")
BATCH = "infra/slurm/host-single-node/s2v4-vm.sbatch"


class LaneError(ValueError):
    """The manifest or a host input is outside the registration; nothing may start."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LaneError(message)


def load_pins(source_dir: Path) -> dict[str, dict[str, Any]]:
    """Cell -> {sha256, size_bytes, selector_sha256}; S is the certified disk."""
    data = json.loads((source_dir / IMAGES).read_text(encoding="utf-8"))
    _require(data.get("schema") == "s2v4-images-v1", f"{IMAGES}: schema")
    pins = {"S": {"sha256": STOCK["sha256"], "size_bytes": STOCK["size_bytes"],
                  "selector_sha256": None}}  # fmt: skip
    for cell, entry in (data.get("cells") or {}).items():
        _require(cell != "S" and bool(SAFE.fullmatch(cell)), f"{IMAGES}: cell {cell}")
        _require(bool(HEX64.fullmatch(str(entry.get("sha256")))), f"{IMAGES}: {cell} sha256")
        _require(bool(HEX64.fullmatch(str(entry.get("selector_sha256")))),
                 f"{IMAGES}: {cell} selector_sha256")  # fmt: skip
        _require(isinstance(entry.get("size_bytes"), int), f"{IMAGES}: {cell} size_bytes")
        pins[cell] = {k: entry[k] for k in ("sha256", "size_bytes", "selector_sha256")}
    return pins


def ledger_row(source_dir: Path) -> dict[str, Any] | None:
    ledger = source_dir / LEDGER
    if not ledger.is_file():
        return None
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if line.strip() and json.loads(line).get("experiment_id") == EXPERIMENT_ID:
            return json.loads(line)
    return None


def slot_id(task_id: str, cell: str, rep: int, kind: str = "capture") -> str:
    return f"{task_id[:8]}:{cell}:{'g' if kind == 'gold' else 'r'}{rep}"


def file_cache_receipts(source_dir: Path) -> dict[str, str]:
    out = {}
    for line in (source_dir / FILE_CACHE_RECEIPTS).read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and HEX64.fullmatch(parts[2]):
            out[parts[0]] = parts[2]
    return out


def check_gold(sid: str, gold: Any, receipts: Mapping[str, str]) -> None:
    """A gold slot's files come from the pinned file cache, each with its receipt's SHA-256,
    and one of them carries the candidate digest."""
    _require(isinstance(gold, dict), f"{sid}: gold slots name their gold")
    _require(bool(SAFE.fullmatch(str(gold.get("job_id", "")))), f"{sid}: gold.job_id")
    files = gold.get("files")
    _require(isinstance(files, dict) and bool(files), f"{sid}: gold.files")
    target = False
    for vm_path, entry in files.items():
        _require(str(vm_path).startswith("/home/user/"), f"{sid}: {vm_path} outside /home/user")
        rel = str(entry.get("rel", ""))
        _require(bool(rel) and not rel.startswith("/") and ".." not in Path(rel).parts,
                 f"{sid}: unsafe rel path")  # fmt: skip
        _require(receipts.get(rel) == entry.get("sha256"),
                 f"{sid}: {rel} differs from the file cache receipts")  # fmt: skip
        target |= entry.get("sha256") == gold.get("candidate_sha256")
    _require(target, f"{sid}: no gold file carries candidate_sha256")


def validate_manifest(raw: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    """The lane's manifest, checked against the registration (raises ``LaneError``)."""
    m = json.loads(json.dumps(raw))
    _require(m.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    _require(m.get("experiment_id") == EXPERIMENT_ID, f"experiment_id must be {EXPERIMENT_ID}")
    purpose = m.get("purpose")
    _require(purpose in PURPOSES, f"purpose must be one of {PURPOSES}")
    _require(ledger_row(source_dir) is None,
             f"{EXPERIMENT_ID} is frozen: development no longer runs (D56)")  # fmt: skip
    _require(isinstance(m.get("name"), str) and bool(SAFE.fullmatch(m["name"])), "unsafe name")
    _require(m.get("mode") == MODE, f"mode must be {MODE}")
    _require(m.get("engine") == {"kind": "none"}, "the probe runs no engine (engine.kind none)")
    vm = m.get("vm") or {}
    for key, value in VM_PINS.items():
        _require(vm.get(key) == value, f"vm.{key} must be {value!r} (action-path v2 2.1)")
    _require("qcow2" not in vm, "vm.qcow2 is per slot here: name the cell images in images")
    _require(isinstance(vm.get("guest_ip"), str), "vm.guest_ip is required")
    v = vm.get("concurrency")
    _require(isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= MAX_CONCURRENCY,
             f"vm.concurrency must be 1-{MAX_CONCURRENCY} (D53)")  # fmt: skip
    pins = load_pins(source_dir)
    images = m.get("images") or {}
    _require(isinstance(images, dict) and bool(images), "images is required")
    for cell, entry in images.items():
        _require(cell in pins, f"images.{cell}: no pinned image for this cell")
        _require(entry.get("sha256") == pins[cell]["sha256"], f"images.{cell}.sha256 differs")
        _require(entry.get("size_bytes") == pins[cell]["size_bytes"],
                 f"images.{cell}.size_bytes differs")  # fmt: skip
        path = str(entry.get("host_path", ""))
        _require(path.startswith(RUN_ROOT) and path.endswith(".qcow2") and ".." not in path,
                 f"images.{cell}.host_path")  # fmt: skip
    _require(m.get("episode_image_id") == EPISODE_IMAGE_ID,
             f"episode_image_id must be the metric image {EPISODE_IMAGE_ID}")  # fmt: skip
    _require(m.get("episode_python", "/opt/venv-lock/bin/python") == "/opt/venv-lock/bin/python",
             "episode_python must be the lock-exact venv")  # fmt: skip
    osworld = m.get("osworld") or {}
    _require(osworld.get("commit") == OSWORLD_COMMIT, f"osworld.commit must be {OSWORLD_COMMIT}")
    _require(str(osworld.get("host_dir", "")).startswith(RUN_ROOT), "osworld.host_dir")
    _require(str((m.get("file_cache") or {}).get("host_dir", "")).startswith(RUN_ROOT),
             "file_cache.host_dir outside the run root")  # fmt: skip
    _require(str(m.get("run_root", "")).startswith(RUN_ROOT), "run_root outside the run root")
    for key in ("episode_timeout_s", "settle_after_reset_s", "settle_before_eval_s"):
        value = m.get(key)
        _require(isinstance(value, int | float) and value > 0, f"{key} must be positive")
    _require(m.get("settle_after_reset_s") == 60 and m.get("settle_before_eval_s") == 20,
             "the settles are S1a's (60 s and 20 s)")  # fmt: skip
    _require(isinstance(m.get("evaluate"), bool), "evaluate must be true or false")
    splits = json.loads((source_dir / SPLITS).read_text(encoding="utf-8"))
    dev = set(splits["dev"])
    receipts = None
    slots = m.get("slots") or []
    _require(bool(slots), "no slots")
    seen: set[str] = set()
    for slot in slots:
        for key in SLOT_FIELDS:
            _require(key in slot, f"slot lacks {key}")
        sid = str(slot["slot"])
        _require(bool(SAFE.fullmatch(sid)) and sid not in seen, f"bad or duplicate slot {sid}")
        seen.add(sid)
        _require(slot["cell"] in images, f"{sid}: cell {slot['cell']} has no image in images")
        _require(isinstance(slot["rep"], int) and slot["rep"] >= 1, f"{sid}: rep")
        kind = slot.get("kind", "capture")
        _require(kind in KINDS, f"{sid}: kind must be one of {KINDS}")
        _require(sid == slot_id(slot["task_id"], slot["cell"], slot["rep"], kind),
                 f"{sid}: slot id must be task8:cell:r<rep> (g<rep> for gold)")  # fmt: skip
        if kind == "gold":
            receipts = receipts if receipts is not None else file_cache_receipts(source_dir)
            check_gold(sid, slot.get("gold"), receipts)
        else:
            _require("gold" not in slot, f"{sid}: only a gold slot names a gold")
        _require(bool(SAFE.fullmatch(str(slot["block"]))), f"{sid}: block")
        if purpose == "development":
            _require(slot["task_id"] in dev, f"{sid}: {slot['task_id']} is not a dev-split task")
    return m


def check_slurm(m: Mapping[str, Any]) -> dict[str, int]:
    slurm = m.get("slurm") or {}
    cpus, memory, minutes = slurm.get("cpus"), slurm.get("memory_gb"), slurm.get("minutes")
    v, cores = m["vm"]["concurrency"], m["vm"]["cpu_cores"]
    _require(isinstance(cpus, int) and v * cores + 1 <= cpus <= 160,
             f"slurm.cpus must fit {v} VMs and a runner CPU (at most 160)")  # fmt: skip
    _require(isinstance(memory, int) and memory >= 6 * v + 6, "slurm.memory_gb too small")
    _require(isinstance(minutes, int) and 1 <= minutes <= 720, "slurm.minutes 1-720")
    return {"cpus": cpus, "memory_gb": memory, "minutes": minutes}


def check_host(m: Mapping[str, Any]) -> dict[str, Any]:
    """Host inputs exist, are read-only and have the pinned sizes (digests: ``verify_images``)."""
    out = {}
    for cell, entry in sorted(m["images"].items()):
        path = Path(entry["host_path"])
        _require(path.is_file() and not path.is_symlink(), f"{cell}: image missing")
        _require(path.stat().st_size == entry["size_bytes"], f"{cell}: image size differs")
        _require(not path.stat().st_mode & 0o222, f"{cell}: image must be read-only")
        out[cell] = entry["size_bytes"]
    for image in (m["vm"]["image_id"], m["episode_image_id"]):
        done = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image],
                              capture_output=True, text=True, timeout=60)  # fmt: skip
        _require(done.stdout.strip() == image, f"image {image} is not present")
    head = subprocess.run(["git", "-C", m["osworld"]["host_dir"], "rev-parse", "HEAD"],
                          capture_output=True, text=True, timeout=60).stdout.strip()  # fmt: skip
    _require(head == OSWORLD_COMMIT, f"OSWorld checkout is at {head}")
    _require(Path(m["file_cache"]["host_dir"]).is_dir(), "file cache directory missing")
    return {"image_bytes": out, "osworld_head": head}


def verify_images(m: Mapping[str, Any], workers: int = 4) -> dict[str, str]:
    """SHA-256 of every image the job mounts, against the pins (raises ``LaneError``)."""
    cells = sorted(m["images"])
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        digests = dict(zip(cells, pool.map(
            lambda c: s1a.sha256_file(Path(m["images"][c]["host_path"])), cells), strict=True))
    for cell, digest in digests.items():
        _require(digest == m["images"][cell]["sha256"], f"{cell}: image digest {digest} differs")
    return digests


def episode_argv(cfg: s1a.LaneConfig, name: str, vm: str, out_dir: Path,
                 cpuset: str | None, kind: str = "capture") -> list[str]:  # fmt: skip
    m = cfg.manifest
    argv = [
        "docker", "run", "--rm", "--name", name,
        "--label", f"cotcodec.slurm_job={cfg.job_id}", "--label", "cotcodec.s2v4=1",
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
    if cpuset:
        argv += ["--cpuset-cpus", cpuset]
    argv += [m["episode_image_id"], m.get("episode_python", "/opt/venv-lock/bin/python"),
             "-m", "harness.s2_locale.vm_gold" if kind == "gold" else "harness.s2_locale.vm_probe",
             "--config", "/out/config.json"]  # fmt: skip
    return argv


def vm_view(m: Mapping[str, Any], cell: str) -> dict[str, Any]:
    """What ``vm_run_argv`` reads: the certified VM settings with this slot's cell image."""
    entry = m["images"][cell]
    qcow2 = {"host_path": entry["host_path"], "sha256": entry["sha256"],
             "size_bytes": entry["size_bytes"]}  # fmt: skip
    return {"campaign_id": f"s2v4-{m['name']}", "vm": {**m["vm"], "qcow2": qcow2}}


class S2Lane(s1a.Lane):
    """The S1a lane with per-slot cell images and the S2 probe."""

    def __init__(self, cfg: s1a.LaneConfig, *, verify: bool = True, **kwargs: Any):
        kwargs.setdefault("certified", [])
        super().__init__(cfg, **kwargs)
        self.verify = verify
        self.pins = load_pins(cfg.source_dir)
        self.image_digests: dict[str, str] | None = None

    def episode_config(self, slot: s1a.Slot, out_dir: Path, t_vm_start: float) -> dict:
        d, m = slot.data, self.m
        return {
            "lane": m["name"], "purpose": m["purpose"], "slot": slot.id,
            "task_id": d["task_id"], "cell": d["cell"], "block": d["block"],
            "attempt": slot.attempt, "image_sha256": m["images"][d["cell"]]["sha256"],
            "selector_sha256": self.pins[d["cell"]]["selector_sha256"], "out_dir": "/out",
            "guest_ip": m["vm"]["guest_ip"], "server_port": m["vm"]["server_port"],
            "osworld_dir": "/inputs/OSWorld", "file_cache_dir": "/inputs/file_cache/files",
            "settle_after_reset_s": m["settle_after_reset_s"],
            "settle_before_eval_s": m["settle_before_eval_s"], "evaluate": m["evaluate"],
            "t_vm_start": t_vm_start,
        }  # fmt: skip

    def gold_config(self, slot: s1a.Slot, t_vm_start: float) -> dict:
        d, m = slot.data, self.m
        return {
            "lane": m["name"], "purpose": m["purpose"], "slot": slot.id,
            "task_id": d["task_id"], "cell": d["cell"], "block": d["block"], "rep": d["rep"],
            "attempt": slot.attempt, "image_sha256": m["images"][d["cell"]]["sha256"],
            "selector_sha256": self.pins[d["cell"]]["selector_sha256"], "out_dir": "/out",
            "guest_ip": m["vm"]["guest_ip"], "server_port": m["vm"]["server_port"],
            "osworld_dir": "/inputs/OSWorld", "file_cache_dir": "/inputs/file_cache/files",
            "settle_after_reset_s": m["settle_after_reset_s"],
            "settle_before_eval_s": m["settle_before_eval_s"], "t_vm_start": t_vm_start,
            "gold": d["gold"],
        }  # fmt: skip

    def run_slot(self, slot: s1a.Slot, worker: int, cycle: int) -> dict[str, Any]:
        from harness.q2.vm.driver import vm_name, vm_run_argv

        cpus = (self.cpusets[worker] if self.cpusets
                else {"vm": None, "vm_mems": None, "runner": None})  # fmt: skip
        name = vm_name(self.cfg.job_id, cycle)
        episode_name = f"cotcodec-s2v4-{self.cfg.job_id}-e{cycle:03d}"
        out_dir = self.cfg.run_dir / "slots" / f"{slot.id.replace(':', '_')}.a{slot.attempt}"
        out_dir.mkdir(parents=True, exist_ok=True)
        t_dispatch = self.clock()
        if self.first_dispatch is None:
            self.first_dispatch = t_dispatch
        host: dict[str, Any] = {"t_dispatch": t_dispatch, "vm": name, "worker": worker,
                                "cpus": cpus, "cell": slot.data["cell"]}  # fmt: skip
        record: dict[str, Any] | None = None
        started_vm = False
        try:
            argv = vm_run_argv(vm_view(self.m, slot.data["cell"]), self.cfg.job_id, cycle,
                               cpus["vm"], cpus["vm_mems"])  # fmt: skip
            t_vm = self.clock()
            try:
                started_vm = True
                self.docker.start_vm(argv)
            except Exception as exc:  # noqa: BLE001 - a VM that will not start is a boot loss
                record = self.loss(slot, "vm_boot", f"{exc}")
            if record is None:
                record = self.episode(slot, out_dir, t_vm, episode_name, name, cpus, host)
        except Exception as exc:  # noqa: BLE001 - a lane-side fault loses the slot
            record = self.loss(slot, "runner_crash", f"lane: {type(exc).__name__}: {exc}")
        finally:
            if started_vm:
                host["teardown"] = self.docker.remove(name)
            host["t_teardown"] = self.clock()
        return self.finish_slot(record, host, t_dispatch)

    def episode(self, slot: s1a.Slot, out_dir: Path, t_vm: float, episode_name: str, vm: str,
                cpus: Mapping[str, Any], host: dict[str, Any]) -> dict[str, Any]:  # fmt: skip
        kind = slot.data.get("kind", "capture")
        config = (self.gold_config(slot, t_vm) if kind == "gold"
                  else self.episode_config(slot, out_dir, t_vm))  # fmt: skip
        (out_dir / "config.json").write_text(json.dumps(config, indent=1), encoding="utf-8")
        argv = episode_argv(self.cfg, episode_name, vm, out_dir, cpus["runner"], kind)
        timeout = float(self.m["episode_timeout_s"])
        rc = self.docker.run_episode(argv, episode_name, timeout, self.stop,
                                     out_dir / "container.log")  # fmt: skip
        host["episode_rc"] = rc
        path = out_dir / "probe.json"
        if rc is None:
            if self.stop.is_set():
                return self.truncated(slot, "cut at the stop signal")
            return self.loss(slot, "runner_crash", f"probe exceeded {timeout} s")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return self.loss(slot, "runner_crash", f"episode container exited {rc}")

    def base_record(self, slot: s1a.Slot) -> dict[str, Any]:
        d = slot.data
        return {"schema": "s2v4-vm-probe-v1", "experiment_id": EXPERIMENT_ID,
                "lane": self.m["name"], "purpose": self.m["purpose"], "slot": slot.id,
                "task_id": d["task_id"], "cell": d["cell"], "block": d["block"],
                "kind": d.get("kind", "capture"), "attempt": slot.attempt,
                "score": None}  # fmt: skip

    def loss(self, slot: s1a.Slot, kind: str, detail: str) -> dict[str, Any]:
        return {**self.base_record(slot), "status": "infrastructure", "infrastructure_type": kind,
                "infrastructure_detail": detail[:500]}  # fmt: skip

    def truncated(self, slot: s1a.Slot, detail: str) -> dict[str, Any]:
        return {**self.base_record(slot), "status": "cap_truncated", "infrastructure_type": None,
                "cap_detail": detail}  # fmt: skip

    def records_name(self) -> str:
        return "probes.jsonl"

    def run(self) -> dict[str, Any]:
        if self.verify:
            try:
                self.image_digests = verify_images(self.m)
            except Exception as exc:  # noqa: BLE001 - nothing dispatches on a wrong image
                receipt = {"schema": "s2v4-vm-lane-receipt-v1", "job_id": self.cfg.job_id,
                           "error": f"image check: {exc}"[:500], "records": 0, "statuses": {},
                           "stopped": True}  # fmt: skip
                self.write_receipt(receipt)
                return receipt
        return super().run()

    def write_receipt(self, receipt: Mapping[str, Any]) -> None:
        out = dict(receipt)
        out["schema"] = "s2v4-vm-lane-receipt-v1"
        out["experiment_id"] = EXPERIMENT_ID
        out["image_digests_verified"] = self.image_digests
        sha = self.cfg.source_dir / ".git_sha"
        out["executor_commit"] = sha.read_text(encoding="utf-8").strip() if sha.is_file() else None
        out["source_tree_sha256"] = s1a.tree_sha256(self.cfg.source_dir)
        super().write_receipt(out)


def canonical(manifest: Mapping[str, Any]) -> str:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def submit(manifest_path: Path, source_dir: Path, dry_run: bool) -> dict[str, Any]:
    m = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), source_dir)
    request = check_slurm(m)
    host = check_host(m)
    text = canonical(m)
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
            f"--job-name=s2v4-{m['name']}"[:60],
            "--export=ALL," + ",".join(f"{k}={v}" for k, v in env.items()), str(batch)]  # fmt: skip
    out = {"manifest_sha256": digest, "manifest": str(stored), "host": host, "argv": argv}
    if not dry_run:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=True)
        out["job_id"] = done.stdout.strip()
    return out


def render(base: Mapping[str, Any], tasks: Sequence[str], cells: Sequence[str],
           reps: int = 1,
           reps_by_cell: Mapping[str, int] | None = None) -> dict[str, Any]:  # fmt: skip
    """Slots for every (task, cell, rep), blocked by task so a task's cells run together;
    ``reps_by_cell`` overrides ``reps`` for a cell (the A/A replicates E2, ER2)."""
    m = json.loads(json.dumps(base))
    by_cell = dict(reps_by_cell or {})
    m["slots"] = [{"slot": slot_id(t, c, r), "task_id": t, "cell": c, "rep": r,
                   "block": f"t{i:03d}"}
                  for i, t in enumerate(tasks) for c in cells
                  for r in range(1, by_cell.get(c, reps) + 1)]  # fmt: skip
    return m


def render_gold(manifest: Mapping[str, Any], golds: Sequence[Mapping[str, Any]],
                cells: Sequence[str]) -> dict[str, Any]:  # fmt: skip
    """Append a gold slot per (task's gold, cell), in each task's block (``golds``: rows with
    ``task_id``, ``job_id``, ``candidate_sha256`` and ``files`` {vm path: {rel, sha256}})."""
    m = json.loads(json.dumps(manifest))
    blocks = {s["task_id"]: s["block"] for s in m["slots"]}
    for g in golds:
        block = blocks.get(g["task_id"], f"g{len(blocks):03d}")
        for c in cells:
            m["slots"].append({"slot": slot_id(g["task_id"], c, 1, "gold"), "task_id": g["task_id"],
                               "cell": c, "rep": 1, "block": block, "kind": "gold",
                               "gold": {"job_id": g["job_id"],
                                        "candidate_sha256": g["candidate_sha256"],
                                        "files": g["files"]}})  # fmt: skip
    return m


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a validated manifest (inside s2v4-vm.sbatch)")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument("--source-dir", type=Path, required=True)
    run.add_argument("--job-id", required=True)
    check = sub.add_parser("validate")
    check.add_argument("manifest", type=Path)
    check.add_argument("--source-dir", type=Path, default=Path("."))
    sb = sub.add_parser("submit")
    sb.add_argument("manifest", type=Path)
    sb.add_argument("--source-dir", type=Path, default=Path("."))
    sb.add_argument("--dry-run", action="store_true")
    rend = sub.add_parser("render")
    rend.add_argument("--base", type=Path, required=True)
    rend.add_argument("--tasks", required=True, help="comma-separated task ids")
    rend.add_argument("--cells", required=True, help="comma-separated cells")
    rend.add_argument("--reps", type=int, default=1)
    rend.add_argument("--reps-by-cell", default="", help="e.g. E=2,ER=2")
    rend.add_argument("--golds", type=Path, default=None, help="gold rows (JSONL)")
    rend.add_argument("--gold-cells", default="E,A,ER,AR,PL")
    rend.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "render":
        by_cell = {k: int(v) for k, v in (x.split("=") for x in args.reps_by_cell.split(",") if x)}
        manifest = render(json.loads(args.base.read_text()), args.tasks.split(","),
                          args.cells.split(","), args.reps, by_cell)  # fmt: skip
        if args.golds:
            rows = [json.loads(x) for x in args.golds.read_text().splitlines() if x.strip()]
            manifest = render_gold(manifest, rows, args.gold_cells.split(","))
        args.out.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
        print(json.dumps({"slots": len(manifest["slots"]), "out": str(args.out)}))
        return 0
    if args.command == "submit":
        print(json.dumps(submit(args.manifest, args.source_dir, args.dry_run), indent=1))
        return 0
    if args.command == "validate":
        manifest = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
        digest = hashlib.sha256(canonical(manifest).encode()).hexdigest()
        print(json.dumps({"ok": True, "manifest_sha256": digest, "slots": len(manifest["slots"])}))
        return 0
    if not re.fullmatch(r"[1-9][0-9]{0,19}", args.job_id):
        raise SystemExit("job id must be numeric")
    manifest = validate_manifest(json.loads(args.manifest.read_text()), args.source_dir)
    from harness.q2.vm.driver import slurm_cpu_ids, snapshot_host

    cpusets = s1a.plan_cpusets(slurm_cpu_ids(args.job_id), manifest["vm"]["concurrency"],
                               manifest["vm"]["cpu_cores"])  # fmt: skip
    lane = S2Lane(s1a.LaneConfig(manifest, args.job_id, args.run_dir, args.source_dir),
                  cpusets=cpusets, snapshot=snapshot_host)  # fmt: skip
    signal.signal(signal.SIGUSR1, lambda *_: lane.stop.set())
    receipt = lane.run()
    print(json.dumps({k: receipt.get(k) for k in ("records", "statuses", "stopped")}))
    return 0 if "error" not in receipt else 3


if __name__ == "__main__":
    raise SystemExit(main())
