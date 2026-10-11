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

Purposes (as S1a's and K2's lanes gate theirs): before the registration is frozen only
``development`` runs, on dev-split tasks (the registration's development smoke). ``phase0`` (the
registered capture and gold sweep, P0.7 and P0.9) is admitted only after the freeze: from a source
tree whose ledger holds this id's row with an unbroken hash chain, whose registration still has
the row's SHA-256, whose ``.git_sha`` is the manifest's freeze commit (the commit that adds the
row; ``render-census`` checks with git that its only parent is the row's ``git_head_at_freeze``
and that it changes only the ledger), and with exactly the committed census slots
(``CENSUS``, pinned by ``CENSUS_SHA256``; rendered by ``census_slots`` with PCG64 seed 42), at
V = 20. A ``phase0`` job that ends before its last slot is resumed once by a ``phase0`` job whose
slots are the census from the first block without a final record (``resume_from_block``). Once
the id is frozen, ``development`` is refused (D56).

PD slots (the planted-document control) run on the ER image with the planted-document file-cache
variant (``pd_cache.py``) mounted instead of the pinned file cache; the variant is pinned by its
manifest's ``files_sha256`` (``PD_CACHE_FILES_SHA256``).

Job minutes include the image check: ``check_slurm`` requires at least
ceil(image GB / ``HASH_GB_PER_MIN``) minutes for hashing every distinct image, plus
ceil(``SLOT_MARGIN`` x slots x ``SLOT_MINUTES`` / V) for the slots, plus 10.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
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
PURPOSES = ("development", "phase0")
PRE_FREEZE_PURPOSES = ("development",)
REGISTERED_PURPOSES = ("phase0",)
# The registered census (P0.7, P0.9): every pool task in S, E, E2, A, ER, AR, PL and AD, every dev
# task also in ER2 and PD, and a gold slot per task with a gold in each admission cell, in blocks
# of 20 with the cells interleaved at random (PCG64 seed 42). Rendered before the freeze and
# pinned here; a registered job runs exactly these slots.
CENSUS = "experiments/manifests/s2v4/phase0-census.json"
CENSUS_SHA256 = "02bfc97bf8c14f48f2bfd57c26a34b5fac0b57d9aa18981b474a286d38589cf0"
GOLDS = "experiments/manifests/s2v4/golds-v4.jsonl"
PD_CACHE_MANIFEST = "program/evidence/2026-10-11/s2v4-image/pd-cache/pd-cache-manifest.json"
# The variant built on the host (pd-cache-v1; its manifest is the evidence file above).
PD_CACHE_FILES_SHA256 = "d51d66fa3d3a890c6a18ad231b926e3932881209ca91e467e8532319c549b46e"
CAPTURE_CELLS = ("S", "E", "A", "ER", "AR", "PL", "AD")
GOLD_CELLS = ("E", "A", "ER", "AR", "PL")
REPLICATES = {"E": 2}  # E2 for every task; ER2 and PD for the dev tasks (DEV_EXTRA)
DEV_EXTRA = (("ER", 2), ("PD", 1))
IMAGE_OF = {"PD": "ER"}  # PD: the ER image with the planted-document file cache
CENSUS_SEED = 42
BLOCK = 20
V_REGISTERED = 20
EPISODE_TIMEOUT_S = 900
HASH_GB_PER_MIN = 30.0  # 0.5 GB/s for the image check (job 1201: 171 GB in 51 s, from cache)
SLOT_MINUTES = 3.5  # registration P0.7's estimate per slot
SLOT_MARGIN = 1.5
MODE = "s2v4-probe"
EPISODE_IMAGE_ID = s1a.EPISODE_IMAGE_ID
VM_PINS = dict(s1a.VM_PINS)  # action-path v2 section 2.1
OSWORLD_COMMIT = s1a.OSWORLD_COMMIT
RUN_ROOT = s1a.RUN_ROOT
MAX_CONCURRENCY = 32  # D53: certified at no more than 32 concurrent VMs
# The registered job's host inputs (the action-path disk, the pinned OSWorld tree and file
# cache, the PD variant) and run root; the census job must name exactly these.
S_HOST_PATH = f"{RUN_ROOT}stage0/q2-action-path/vm/Ubuntu.qcow2"
OSWORLD_HOST = f"{RUN_ROOT}stage0/q2-evaluator-mutation/inputs/OSWorld"
FILE_CACHE_HOST = f"{RUN_ROOT}stage0/q2-evaluator-mutation/inputs/file_cache_1e112283/files"
PD_CACHE_HOST = f"{RUN_ROOT}stage0/s2v4/pd-cache-v1/files"
PHASE0_RUN_ROOT = f"{RUN_ROOT}stage0/s2v4/phase0-runs"
STOCK = {"cell": "S", "sha256": s1a.QCOW2_SHA256, "size_bytes": s1a.QCOW2_BYTES}
SLOT_FIELDS = ("slot", "task_id", "cell", "rep", "block")
KINDS = ("capture", "gold")  # vm_probe.py, vm_gold.py
FILE_CACHE_RECEIPTS = "program/evidence/q2-mutation/harness/file-cache-receipts.tsv"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
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
    for cell, image in IMAGE_OF.items():
        if image in pins:
            pins[cell] = dict(pins[image])
    return pins


def ledger_row(source_dir: Path) -> dict[str, Any] | None:
    """This id's ledger row after checking the hash chain end to end (None when not frozen)."""
    ledger = source_dir / LEDGER
    if not ledger.is_file():
        return None
    previous, row = "0" * 64, None
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        entry = json.loads(line)
        body = {k: v for k, v in entry.items() if k != "hash"}
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        _require(entry.get("previous_hash") == previous and entry.get("hash") == digest,
                 f"ledger line {number}: the hash chain does not hold")  # fmt: skip
        previous = digest
        if row is None and entry.get("experiment_id") == EXPERIMENT_ID:
            row = entry
    return row


def frozen_registration(source_dir: Path) -> dict[str, Any]:
    """The ledger row, once the source tree's registration is the frozen file (raises)."""
    row = ledger_row(source_dir)
    _require(row is not None, f"no ledger row for {EXPERIMENT_ID}: it is not frozen")
    assert row is not None
    _require(row.get("path") == REGISTRATION, f"the ledger row names {row.get('path')!r}")
    path = source_dir / REGISTRATION
    _require(path.is_file() and not path.is_symlink(), f"{REGISTRATION} is missing")
    actual = s1a.sha256_file(path)
    _require(actual == row.get("sha256"),
             f"{REGISTRATION} changed after the freeze ({actual} != {row.get('sha256')})")
    return row


def check_export(m: Mapping[str, Any], source_dir: Path, row: Mapping[str, Any]) -> None:
    """A registered job runs from an export of the freeze commit (D56: every export runs from
    the commit that adds the ledger row): the export's ``.git_sha`` is the manifest's freeze
    commit, and the manifest names this ledger row and its ``git_head_at_freeze`` (the parent,
    which has no row). ``render-census`` checked the commit's parent and diff with git."""
    sha_file = source_dir / ".git_sha"
    sha = sha_file.read_text(encoding="utf-8").strip() if sha_file.is_file() else ""
    freeze = m.get("freeze") or {}
    _require(bool(HEX40.fullmatch(sha)), "the export has no .git_sha (export the freeze commit)")
    _require(freeze.get("commit") == sha,
             f"the export's .git_sha {sha[:12]} is not the manifest's freeze commit")
    _require(freeze.get("ledger_row_hash") == row.get("hash"),
             "the manifest names another ledger row")  # fmt: skip
    head = row.get("git_head_at_freeze")
    _require(freeze.get("git_head_at_freeze") == head and head != sha,
             "the export must be the freeze commit, never its parent git_head_at_freeze")


def check_freeze_commit(repo: Path, commit: str, row: Mapping[str, Any]) -> dict[str, Any]:
    """With git: ``commit`` is the freeze commit (its only parent is the row's
    ``git_head_at_freeze`` and it changes only the ledger). Run where the repository is."""
    def git(*args: str) -> str:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                              timeout=60)  # fmt: skip
        _require(done.returncode == 0, f"git {' '.join(args)}: {done.stderr.strip()[:200]}")
        return done.stdout

    parents = git("rev-list", "--parents", "-n", "1", commit).split()[1:]
    _require(parents == [row.get("git_head_at_freeze")],
             f"{commit[:12]} is not the freeze commit (parents {parents})")
    changed = git("diff", "--name-only", parents[0], commit).split()
    _require(changed == [LEDGER], f"the freeze commit changes more than the ledger: {changed[:5]}")
    return {"commit": commit, "git_head_at_freeze": parents[0], "changed": changed}


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


def census_file(source_dir: Path) -> dict[str, Any]:
    """The committed census (``CENSUS``), checked against ``CENSUS_SHA256``."""
    path = source_dir / CENSUS
    _require(path.is_file(), f"{CENSUS} is missing")
    data = path.read_bytes()
    _require(hashlib.sha256(data).hexdigest() == CENSUS_SHA256,
             f"{CENSUS} is not the pinned census (CENSUS_SHA256)")  # fmt: skip
    return json.loads(data)


def pd_cache_manifest(source_dir: Path) -> dict[str, Any]:
    data = json.loads((source_dir / PD_CACHE_MANIFEST).read_text(encoding="utf-8"))
    from harness.s2_locale.pd_cache import files_digest

    _require(data.get("files_sha256") == files_digest(data.get("files") or {})
             == PD_CACHE_FILES_SHA256, "the PD file-cache manifest is not the pinned variant")
    return data


def validate_manifest(raw: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    """The lane's manifest, checked against the registration (raises ``LaneError``)."""
    m = json.loads(json.dumps(raw))
    _require(m.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    _require(m.get("experiment_id") == EXPERIMENT_ID, f"experiment_id must be {EXPERIMENT_ID}")
    purpose = m.get("purpose")
    _require(purpose in PURPOSES, f"purpose must be one of {PURPOSES}")
    row = ledger_row(source_dir)
    if purpose in PRE_FREEZE_PURPOSES:
        _require(row is None, f"{EXPERIMENT_ID} is frozen: development no longer runs (D56)")
    else:
        _require(row is not None, f"{purpose} runs only after the freeze (no ledger row for "
                                  f"{EXPERIMENT_ID})")  # fmt: skip
        assert row is not None
        check_export(m, source_dir, frozen_registration(source_dir))
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
        if cell in IMAGE_OF:
            _require(images.get(IMAGE_OF[cell]) == entry,
                     f"images.{cell} must be the {IMAGE_OF[cell]} image")  # fmt: skip
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
        if slot["cell"] == "PD":
            _require(kind == "capture" and slot["task_id"] in dev,
                     f"{sid}: PD is a capture slot of a dev task")  # fmt: skip
        if purpose == "development":
            _require(slot["task_id"] in dev, f"{sid}: {slot['task_id']} is not a dev-split task")
    if any(slot["cell"] == "PD" for slot in slots):
        pd = m.get("file_cache_pd") or {}
        _require(str(pd.get("host_dir", "")).startswith(RUN_ROOT) and ".." not in
                 str(pd.get("host_dir")), "PD slots need file_cache_pd.host_dir under the run "
                 "root")  # fmt: skip
        _require(pd.get("files_sha256") == pd_cache_manifest(source_dir)["files_sha256"],
                 "file_cache_pd.files_sha256 is not the pinned PD variant")  # fmt: skip
    if purpose in REGISTERED_PURPOSES:
        check_registered(m, source_dir)
    return m


def check_registered(m: Mapping[str, Any], source_dir: Path) -> None:
    """A ``phase0`` job: exactly the committed census (or its suffix from a block, to resume an
    interrupted job once), at V = 20, with evaluate on and the registered episode timeout."""
    census = census_file(source_dir)
    slots = census["slots"]
    resume = m.get("resume_from_block")
    if resume is None:
        _require(m["slots"] == slots, "phase0's slots differ from the committed census")
    else:
        index = next((i for i, s in enumerate(slots) if s["block"] == resume), None)
        _require(index is not None and index > 0, f"resume_from_block {resume!r} is not a block")
        _require(m["slots"] == slots[index:], "phase0's resumed slots are not the census suffix")
        prior = m.get("resumes") or {}
        _require(bool(HEX64.fullmatch(str(prior.get("records_sha256", "")))),
                 "a resumed job names the interrupted job's records (resumes.records_sha256)")
    _require(m["vm"]["concurrency"] == V_REGISTERED, f"phase0 runs at V = {V_REGISTERED}")
    _require(m["evaluate"] is True, "phase0 runs the task's postconfig and checker")
    _require(m["episode_timeout_s"] == EPISODE_TIMEOUT_S,
             f"phase0's episode timeout is {EPISODE_TIMEOUT_S} s")  # fmt: skip
    _require(set(m["images"]) == {*CAPTURE_CELLS, *IMAGE_OF},
             "phase0 mounts every cell image, S and PD included")  # fmt: skip
    _require(m["images"]["S"]["host_path"] == S_HOST_PATH
             and m["osworld"]["host_dir"] == OSWORLD_HOST
             and m["file_cache"]["host_dir"] == FILE_CACHE_HOST
             and ("PD" not in m["images"]
                  or (m.get("file_cache_pd") or {}).get("host_dir") == PD_CACHE_HOST),
             "phase0 reads the registered host inputs")  # fmt: skip


def image_bytes(m: Mapping[str, Any]) -> int:
    """Bytes the image check hashes: every distinct image the job mounts."""
    return sum({e["host_path"]: e["size_bytes"] for e in m["images"].values()}.values())


def check_slurm(m: Mapping[str, Any]) -> dict[str, int]:
    slurm = m.get("slurm") or {}
    cpus, memory, minutes = slurm.get("cpus"), slurm.get("memory_gb"), slurm.get("minutes")
    v, cores = m["vm"]["concurrency"], m["vm"]["cpu_cores"]
    _require(isinstance(cpus, int) and v * cores + 1 <= cpus <= 160,
             f"slurm.cpus must fit {v} VMs and a runner CPU (at most 160)")  # fmt: skip
    _require(isinstance(memory, int) and memory >= 6 * v + 6, "slurm.memory_gb too small")
    hash_min = math.ceil(image_bytes(m) / 1e9 / HASH_GB_PER_MIN)
    slot_min = math.ceil(SLOT_MARGIN * len(m["slots"]) * SLOT_MINUTES / v)
    need = hash_min + slot_min + 10
    _require(isinstance(minutes, int) and need <= minutes <= 720,
             f"slurm.minutes must cover the image check ({hash_min}) and the slots ({slot_min}) "
             f"plus 10 ({need}), at most 720")  # fmt: skip
    return {"cpus": cpus, "memory_gb": memory, "minutes": minutes, "hash_minutes": hash_min,
            "slot_minutes": slot_min}  # fmt: skip


def check_host(m: Mapping[str, Any], source_dir: Path = Path(".")) -> dict[str, Any]:
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
    if m.get("file_cache_pd"):
        from harness.s2_locale.pd_cache import verify

        manifest = pd_cache_manifest(source_dir)
        bad = verify(Path(m["file_cache_pd"]["host_dir"]), manifest["files"])
        _require(not bad, f"the PD variant directory differs from its manifest: {bad[:3]}")
    return {"image_bytes": out, "osworld_head": head}


def verify_images(m: Mapping[str, Any], workers: int = 4) -> dict[str, str]:
    """SHA-256 of every image the job mounts (each distinct file once), against the pins
    (raises ``LaneError``)."""
    paths = sorted({m["images"][c]["host_path"] for c in m["images"]})
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        by_path = dict(zip(paths, pool.map(lambda p: s1a.sha256_file(Path(p)), paths),
                           strict=True))  # fmt: skip
    digests = {c: by_path[m["images"][c]["host_path"]] for c in sorted(m["images"])}
    for cell, digest in digests.items():
        _require(digest == m["images"][cell]["sha256"], f"{cell}: image digest {digest} differs")
    return digests


def file_cache_dir(m: Mapping[str, Any], cell: str) -> str:
    """The file cache a slot's setup reads: the PD variant for PD slots, else the pinned one."""
    return m["file_cache_pd"]["host_dir"] if cell == "PD" else m["file_cache"]["host_dir"]


def episode_argv(cfg: s1a.LaneConfig, name: str, vm: str, out_dir: Path,
                 cpuset: str | None, kind: str = "capture",
                 cell: str = "") -> list[str]:  # fmt: skip
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
        "--volume", f"{file_cache_dir(m, cell)}:/inputs/file_cache/files:ro",
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
        argv = episode_argv(self.cfg, episode_name, vm, out_dir, cpus["runner"], kind,
                            slot.data["cell"])  # fmt: skip
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
    host = check_host(m, source_dir)
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


def census_slots(tasks: Sequence[Mapping[str, Any]], golds: Sequence[Mapping[str, Any]],
                 seed: int = CENSUS_SEED, block: int = BLOCK) -> list[dict[str, Any]]:
    """The census in its registered order (P0.7): the tasks in a seeded order; per task its
    capture slots (S, E, A, ER, AR, PL, AD, E2; a dev task also ER2 and PD) and a gold slot per
    admission cell when it has a gold; the sequence cut into blocks of ``block`` and each block
    shuffled, all with one ``numpy.random.Generator(PCG64(seed))``. ``tasks``: pool rows
    (``task_id``, ``split``), sorted by id before the draw; ``golds``: ``golds.py`` rows."""
    import numpy as np

    rng = np.random.Generator(np.random.PCG64(seed))
    ordered = sorted(tasks, key=lambda t: t["task_id"])
    by_task = {g["task_id"]: g for g in golds}
    seq: list[dict[str, Any]] = []
    for i in rng.permutation(len(ordered)):
        t = ordered[int(i)]
        tid = t["task_id"]
        extra = [(c, r) for c, n in REPLICATES.items() for r in range(2, n + 1)]
        if t["split"] == "dev":
            extra += list(DEV_EXTRA)
        for cell, rep in [(c, 1) for c in CAPTURE_CELLS] + extra:
            seq.append({"slot": slot_id(tid, cell, rep), "task_id": tid, "cell": cell, "rep": rep})
        g = by_task.get(tid)
        if g is not None:
            for cell in GOLD_CELLS:
                seq.append({"slot": slot_id(tid, cell, 1, "gold"), "task_id": tid, "cell": cell,
                            "rep": 1, "kind": "gold",
                            "gold": {"job_id": g["job_id"],
                                     "candidate_sha256": g["candidate_sha256"],
                                     "files": g["files"]}})  # fmt: skip
    out: list[dict[str, Any]] = []
    for b, start in enumerate(range(0, len(seq), block)):
        chunk = seq[start:start + block]
        for j in rng.permutation(len(chunk)):
            out.append({**chunk[int(j)], "block": f"b{b:03d}"})
    return out


def registered_base(source_dir: Path, purpose: str = "phase0", name: str = "s2v4-phase0",
                    run_root: str = PHASE0_RUN_ROOT,
                    n_slots: int = 1322) -> dict[str, Any]:  # fmt: skip
    """The census job's manifest without its slots: every pinned image (``images.json``), S, PD
    on the ER image, the registered host inputs, V = 20 and the Slurm request ``check_slurm``
    requires (the image check and the slots)."""
    data = json.loads((source_dir / IMAGES).read_text(encoding="utf-8"))
    images = {"S": {"host_path": S_HOST_PATH, "sha256": STOCK["sha256"],
                    "size_bytes": STOCK["size_bytes"]}}  # fmt: skip
    for cell, entry in sorted((data.get("cells") or {}).items()):
        images[cell] = {"host_path": entry["file"], "sha256": entry["sha256"],
                        "size_bytes": entry["size_bytes"]}  # fmt: skip
    for cell, image in IMAGE_OF.items():
        images[cell] = dict(images[image])
    m: dict[str, Any] = {
        "schema": SCHEMA, "experiment_id": EXPERIMENT_ID, "purpose": purpose, "name": name,
        "mode": MODE, "engine": {"kind": "none"},
        "vm": {**VM_PINS, "guest_ip": "20.20.20.21", "hmp_port": 7100,
               "concurrency": V_REGISTERED},
        "images": images, "episode_image_id": EPISODE_IMAGE_ID,
        "episode_python": "/opt/venv-lock/bin/python",
        "osworld": {"commit": OSWORLD_COMMIT, "host_dir": OSWORLD_HOST},
        "file_cache": {"host_dir": FILE_CACHE_HOST},
        "file_cache_pd": {"host_dir": PD_CACHE_HOST, "files_sha256": PD_CACHE_FILES_SHA256},
        "run_root": run_root, "episode_timeout_s": EPISODE_TIMEOUT_S,
        "settle_after_reset_s": 60, "settle_before_eval_s": 20, "evaluate": True,
    }  # fmt: skip
    hash_min = math.ceil(image_bytes(m) / 1e9 / HASH_GB_PER_MIN)
    slot_min = math.ceil(SLOT_MARGIN * n_slots * SLOT_MINUTES / V_REGISTERED)
    m["slurm"] = {"cpus": V_REGISTERED * VM_PINS["cpu_cores"] + 1,
                  "memory_gb": 6 * V_REGISTERED + 6, "minutes": hash_min + slot_min + 10}
    return m


def render_census(base: Mapping[str, Any], slots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    m = json.loads(json.dumps(base))
    m["slots"] = json.loads(json.dumps(list(slots)))
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
    cen = sub.add_parser("render-census", help="the census slots (or the dev part) as a manifest")
    cen.add_argument("--base", type=Path, default=None,
                     help="a base manifest (default: registered_base from images.json)")
    cen.add_argument("--purpose", default="phase0", choices=PURPOSES)
    cen.add_argument("--name", default="s2v4-phase0")
    cen.add_argument("--run-root", default=PHASE0_RUN_ROOT)
    cen.add_argument("--pool", type=Path, required=True)
    cen.add_argument("--golds", type=Path, required=True)
    cen.add_argument("--dev-only", action="store_true", help="development: the dev tasks only")
    cen.add_argument("--census-out", type=Path, default=None,
                     help="also write the census file (CENSUS) for pinning")
    cen.add_argument("--freeze-commit", default=None,
                     help="phase0: the freeze commit, checked with git in --repo")
    cen.add_argument("--repo", type=Path, default=Path("."))
    cen.add_argument("--source-dir", type=Path, default=Path("."),
                     help="phase0: the export of the freeze commit (its ledger row)")
    cen.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "render-census":
        from harness.s2_locale.golds import pool_tasks

        tasks = pool_tasks(json.loads(args.pool.read_text()))
        if args.dev_only:
            tasks = [t for t in tasks if t["split"] == "dev"]
        golds = [json.loads(x) for x in args.golds.read_text().splitlines() if x.strip()]
        slots = census_slots(tasks, golds)
        if args.census_out:
            census = {"schema": "s2v4-census-v1", "seed": CENSUS_SEED, "block": BLOCK,
                      "pool_sha256": hashlib.sha256(args.pool.read_bytes()).hexdigest(),
                      "golds_sha256": hashlib.sha256(args.golds.read_bytes()).hexdigest(),
                      "tasks": len(tasks), "slots": slots}  # fmt: skip
            args.census_out.write_text(json.dumps(census, indent=0, sort_keys=True) + "\n")
        base = (json.loads(args.base.read_text()) if args.base else registered_base(
            args.source_dir, args.purpose, args.name, args.run_root, len(slots)))
        if args.freeze_commit:
            row = frozen_registration(args.source_dir)
            check_freeze_commit(args.repo, args.freeze_commit, row)
            base["freeze"] = {"commit": args.freeze_commit, "ledger_row_hash": row["hash"],
                              "git_head_at_freeze": row["git_head_at_freeze"]}  # fmt: skip
        manifest = render_census(base, slots)
        args.out.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
        kinds = {k: sum(1 for x in slots if x.get("kind", "capture") == k) for k in KINDS}
        print(json.dumps({"slots": len(slots), **kinds, "out": str(args.out)}))
        return 0
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
