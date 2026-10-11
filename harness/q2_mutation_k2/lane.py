"""The K2 VM lane: the host side of a CPU-only K2 job (registration sections 4 and 10).

Run by ``infra/slurm/host-single-node/q2m-k2-vm.sbatch`` as a bare host process (standard
library only; the host's Python 3.10). It is the S1a lane (``harness.q2_stage1.lane.Lane``:
continuous dispatch, one re-queue of a slot lost to infrastructure, the stop signal, host
snapshots, the D12 stop) with K2's slots: for each slot it boots a fresh VM container from the
read-only qcow2 with the action-path v2 runtime's settings (``harness.q2.vm.driver.vm_run_argv``),
starts one GPU-less episode container in that VM's ``--network none`` namespace running
``harness.q2_mutation_k2.executor``, waits for its run record, and tears the VM down.

A slot is one run of one pair: ``RUNS_PER_PAIR`` runs per pair, in blocks per set (the
registered sample's first runs, then its second runs, then the K2-C list's), so a stop leaves
the registered sample's runs done first. The episode
container mounts the source tree, the OSWorld tree, the pinned file cache and the mutation
run's candidate files read-only, and its own output directory read-write.

``validate_manifest`` keeps a job inside the registration: the VM settings are the action-path
v2 runtime's, the episode image is the metric image, the concurrency is at most 32 (D53).
Before this addendum is frozen only ``development`` runs, on dev-split tasks and a dev mutation
run's candidates. After the freeze only ``k2`` runs: from a source tree whose registration
still has its ledger row's SHA-256 (an export of the freeze commit, the commit that adds the
row; its parent, the row's ``git_head_at_freeze``, has no row), with the registered settings,
a manifest rendered from the pinned job list, and exactly the registered slots (the frozen K2
sample, then the K2-C candidate list, two runs each). One ``k2`` job: ``submit`` and ``run``
refuse while any run directory under the run root already holds a ``k2`` manifest of this id.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import signal
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from harness.q2_stage1 import lane as s1a

SCHEMA = "q2m-k2-lane-v1"
EXPERIMENT_ID = "q2-evaluator-mutation-v1-k2"
REGISTRATION = "program/preregistrations/q2-evaluator-mutation-v1-k2.md"
LEDGER = "program/preregistrations/ledger.jsonl"
SPLITS = "program/evidence/q2-mutation/splits.json"
FILE_CACHE_RECEIPTS = "program/evidence/q2-mutation/harness/file-cache-receipts.tsv"
PURPOSES = ("development", "k2")
MODE = "k2-inject"
RUN_SCHEMA = "q2m-k2-run-v1"
EPISODE_IMAGE_ID = s1a.EPISODE_IMAGE_ID  # the checker-mutation study's metric image
VM_PINS = dict(s1a.VM_PINS)  # action-path v2 section 2.1
QCOW2_SHA256 = s1a.QCOW2_SHA256
QCOW2_BYTES = s1a.QCOW2_BYTES
OSWORLD_COMMIT = s1a.OSWORLD_COMMIT
RUN_ROOT = s1a.RUN_ROOT
MAX_CONCURRENCY = 32  # D53: certified at no more than 32 concurrent VMs
RUNS_PER_PAIR = 2
SETS = ("k2", "k2c")
ROOTS = {"candidates": "/inputs/candidates", "file_cache": "/inputs/file_cache/files"}
# The registered run (section 4): fixed for purpose k2, never a manifest's choice.
REGISTERED_SETTINGS = {
    "episode_timeout_s": 900,
    "settle_after_reset_s": 60,
    "settle_before_eval_s": 20,
    "runs_per_pair": RUNS_PER_PAIR,
    "requeue": True,
}
REGISTERED_CONCURRENCY = 8
REGISTERED_SLURM = {"cpus": 40, "memory_gb": 64, "minutes": 360}
REGISTERED_CANDIDATES_RUN = "confirm-mutants-v1"
# The frozen K2 sample (parent section 10, drawn in job 3 of confirm-mutants-v1) and the K2-C
# candidate list (section 8), both committed; their SHA-256 are the registration's.
REGISTERED_SAMPLE = (
    "program/evidence/2026-10-08/q2-mutation-confirm/results/released/k2/k2-sample.jsonl"
)
REGISTERED_SAMPLE_SHA256 = "1194168019c4aa87fa3f4aa0ad02f9ed53c207a86ebec264e731545afed6525a"
REGISTERED_K2C = "program/evidence/2026-10-11/q2-mutation-k2/k2c-candidates-confirm.jsonl"
# The confirm run's build/scoring-jobs.jsonl the sample was drawn from (its summary's
# ``jobs_sha256``, section 2): the k2 job's candidate files are mapped from this list only.
REGISTERED_JOBS_SHA256 = "9c2426b7dce17f6357950b0bdb2560ce1a20005a5702a49b5058d840fa811b14"
REFUSED = "refused.json"  # written by a k2 run that found an earlier k2 job (section 4)
SLOT_FIELDS = (
    "slot",
    "set",
    "pair",
    "run",
    "block",
    "job_id",
    "mutant_id",
    "task_id",
    "kind",
    "candidate_sha256",
    "files",
)
IDENTITY_FIELDS = (
    "set",
    "pair",
    "run",
    "block",
    "job_id",
    "mutant_id",
    "task_id",
    "kind",
    "candidate_sha256",
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,96}$")
BATCH = "infra/slurm/host-single-node/q2m-k2-vm.sbatch"


class LaneError(ValueError):
    """The manifest or a host input is outside the registration; nothing may start."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LaneError(message)


def sha256_file(path: Path) -> str:
    return s1a.sha256_file(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# --------------------------------------------------------------------------- freeze state


def ledger_row(source_dir: Path) -> dict[str, Any] | None:
    """This id's ledger row after checking the chain end to end (None when not frozen)."""
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
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        _require(
            entry.get("previous_hash") == previous and entry.get("hash") == digest,
            f"ledger line {number}: the hash chain does not hold",
        )
        previous = digest
        if row is None and entry.get("experiment_id") == EXPERIMENT_ID:
            row = entry
    return row


def frozen_registration(source_dir: Path) -> dict[str, Any]:
    """The ledger row, once the source tree's registration is the frozen file (raises)."""
    row = ledger_row(source_dir)
    _require(row is not None, f"no ledger row for {EXPERIMENT_ID}: the addendum is not frozen")
    assert row is not None
    _require(row.get("path") == REGISTRATION, f"the ledger row names {row.get('path')!r}")
    path = source_dir / REGISTRATION
    _require(path.is_file() and not path.is_symlink(), f"{REGISTRATION} is missing")
    actual = sha256_file(path)
    _require(
        actual == row.get("sha256"),
        f"{REGISTRATION} changed after the freeze ({actual} != {row.get('sha256')})",
    )
    return row


def file_cache_receipts(source_dir: Path) -> dict[str, str]:
    out = {}
    for line in (source_dir / FILE_CACHE_RECEIPTS).read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and HEX64.fullmatch(parts[2]):
            out[parts[0]] = parts[2]
    return out


# --------------------------------------------------------------------------- slots


def registered_pairs(source_dir: Path) -> list[dict[str, Any]]:
    """The registered pairs, in order: the frozen K2 sample (set ``k2``), then the K2-C list
    (set ``k2c``). Raises when either file differs from its registered SHA-256."""
    sample_path = source_dir / REGISTERED_SAMPLE
    _require(
        sha256_file(sample_path) == REGISTERED_SAMPLE_SHA256,
        "the K2 sample is not the frozen sample",
    )
    k2c_path = source_dir / REGISTERED_K2C
    expected = registered_k2c_sha256(source_dir)
    _require(sha256_file(k2c_path) == expected, "the K2-C list differs from the registered one")
    pairs = []
    for index, row in enumerate(read_jsonl(sample_path)):
        pairs.append({"set": "k2", "pair": index, **_identity(row)})
    for index, row in enumerate(read_jsonl(k2c_path)):
        pairs.append({"set": "k2c", "pair": index, **_identity(row)})
    return pairs


def registered_k2c_sha256(source_dir: Path) -> str:
    """The K2-C list's SHA-256 as the registration states it (section 2)."""
    text = (source_dir / REGISTRATION).read_text(encoding="utf-8")
    match = re.search(r"K2-C list SHA-256: `([0-9a-f]{64})`", text)
    _require(match is not None, "the registration does not state the K2-C list's SHA-256")
    assert match is not None
    return match.group(1)


def _identity(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "mutant_id": row["mutant_id"],
        "task_id": row["task_id"],
        "kind": row["kind"],
        "candidate_sha256": row["candidate_sha256"],
    }


def slot_id(set_name: str, pair: int, run: int) -> str:
    return f"{set_name}:{pair:03d}:r{run}"


def expand_runs(pairs: Sequence[Mapping[str, Any]], runs: int = RUNS_PER_PAIR) -> list[dict]:
    """Per set, in the order the sets first appear (the registered sample before the K2-C
    list): every pair's run 1 (block ``<set>-r1``), then every pair's run 2 (``<set>-r2``).
    A stop therefore leaves the registered sample's first runs, then its second runs, done
    before any K2-C run."""
    sets: list[str] = []
    for pair in pairs:
        if pair["set"] not in sets:
            sets.append(pair["set"])
    out = []
    for set_name in sets:
        for run in range(1, runs + 1):
            for pair in pairs:
                if pair["set"] != set_name:
                    continue
                out.append(
                    {
                        **pair,
                        "run": run,
                        "block": block_name(set_name, run),
                        "slot": slot_id(set_name, int(pair["pair"]), run),
                    }
                )
    return out


def block_name(set_name: str, run: int) -> str:
    return f"{set_name}-r{run}"


def map_files(job: Mapping[str, Any], roots: Mapping[str, str]) -> dict[str, dict[str, str]]:
    """A scoring job's files (container paths of the mutation run) as manifest entries:
    ``root`` (candidates or file_cache) and ``rel``; ``roots`` maps each root to the prefix the
    mutation run's build container used (``/out/files``, ``/inputs/file_cache_1e112283/files``)."""
    out = {}
    for vm_path, local in sorted(job["files"].items()):
        if local is None:
            raise LaneError(f"{job['job_id']}: a deleted path cannot be injected")
        for root, prefix in roots.items():
            if str(local).startswith(prefix.rstrip("/") + "/"):
                out[vm_path] = {"root": root, "rel": str(local)[len(prefix.rstrip("/")) + 1 :]}
                break
        else:
            raise LaneError(f"{job['job_id']}: {local} is under no known root")
    return out


def render_slots(
    pairs: Sequence[Mapping[str, Any]],
    jobs: Mapping[str, Mapping[str, Any]],
    *,
    roots: Mapping[str, str],
    host_roots: Mapping[str, Path],
    runs: int = RUNS_PER_PAIR,
) -> list[dict[str, Any]]:
    """The manifest's slots: each pair's job files mapped and hashed on the host."""
    with_files = []
    for pair in pairs:
        job = jobs.get(pair["job_id"])
        _require(job is not None, f"{pair['job_id']} is not in the scoring jobs")
        assert job is not None
        _require(
            job.get("candidate_sha256") == pair["candidate_sha256"],
            f"{pair['job_id']}: candidate_sha256 differs from the job list",
        )
        files = map_files(job, roots)
        for entry in files.values():
            entry["sha256"] = sha256_file(host_roots[entry["root"]] / entry["rel"])
        with_files.append({**pair, "files": files})
    return expand_runs(with_files, runs)


def container_path(entry: Mapping[str, str]) -> str:
    return f"{ROOTS[entry['root']]}/{entry['rel']}"


# --------------------------------------------------------------------------- validation


def validate_manifest(raw: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    """The lane's manifest, checked against the registration (raises ``LaneError``)."""
    m = json.loads(json.dumps(raw))
    _require(m.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    _require(m.get("experiment_id") == EXPERIMENT_ID, f"experiment_id must be {EXPERIMENT_ID}")
    purpose = m.get("purpose")
    _require(purpose in PURPOSES, f"purpose must be one of {PURPOSES}")
    _require(isinstance(m.get("name"), str) and bool(SAFE.fullmatch(m["name"])), "unsafe name")
    _require(m.get("mode") == MODE, f"mode must be {MODE}")
    _require((m.get("engine") or {}).get("kind") == "none", "a K2 job runs no engine")
    is_frozen = ledger_row(source_dir) is not None
    if is_frozen:
        _require(purpose == "k2", "the addendum is frozen: only the registered k2 job runs")
        frozen_registration(source_dir)
    else:
        _require(purpose == "development", "k2 runs only after the addendum is frozen")
    vm = m.get("vm") or {}
    for key, value in VM_PINS.items():
        _require(vm.get(key) == value, f"vm.{key} must be {value!r} (action-path v2 2.1)")
    qcow2 = vm.get("qcow2") or {}
    _require(qcow2.get("sha256") == QCOW2_SHA256, "vm.qcow2.sha256 is not the pinned guest disk")
    _require(qcow2.get("size_bytes") == QCOW2_BYTES, "vm.qcow2.size_bytes differs")
    _require(str(qcow2.get("host_path", "")).startswith(RUN_ROOT), "qcow2 outside the run root")
    _require(isinstance(vm.get("guest_ip"), str), "vm.guest_ip is required")
    v = vm.get("concurrency")
    _require(
        isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= MAX_CONCURRENCY,
        f"vm.concurrency must be 1-{MAX_CONCURRENCY} (D53)",
    )
    _require(
        m.get("episode_image_id") == EPISODE_IMAGE_ID,
        f"episode_image_id must be the metric image {EPISODE_IMAGE_ID}",
    )
    _require(
        m.get("episode_python", "/opt/venv-lock/bin/python") == "/opt/venv-lock/bin/python",
        "episode_python must be the lock-exact venv",
    )
    osworld = m.get("osworld") or {}
    _require(osworld.get("commit") == OSWORLD_COMMIT, f"osworld.commit must be {OSWORLD_COMMIT}")
    _require(str(osworld.get("host_dir", "")).startswith(RUN_ROOT), "osworld.host_dir")
    _require(
        str((m.get("file_cache") or {}).get("host_dir", "")).startswith(RUN_ROOT),
        "file_cache.host_dir outside the run root",
    )
    candidates = m.get("candidates") or {}
    _require(
        str(candidates.get("host_dir", "")).startswith(RUN_ROOT),
        "candidates.host_dir outside the run root",
    )
    run_name = str(candidates.get("run", ""))
    _require(bool(SAFE.fullmatch(run_name)), "candidates.run")
    _require(
        f"/runs/{run_name}/build/files" in str(candidates["host_dir"]),
        "candidates.host_dir must be the named mutation run's build/files",
    )
    _require(str(m.get("run_root", "")).startswith(RUN_ROOT), "run_root outside the run root")
    for key in ("episode_timeout_s", "settle_after_reset_s", "settle_before_eval_s"):
        value = m.get(key, REGISTERED_SETTINGS[key])
        _require(isinstance(value, int | float) and value > 0, f"{key} must be positive")
    _require(
        m.get("runs_per_pair", RUNS_PER_PAIR) == RUNS_PER_PAIR,
        f"runs_per_pair is {RUNS_PER_PAIR} (section 4)",
    )
    splits = json.loads((source_dir / SPLITS).read_text(encoding="utf-8"))
    receipts = file_cache_receipts(source_dir)
    slots = m.get("slots") or []
    _require(bool(slots), "no slots")
    seen: set[str] = set()
    for slot in slots:
        for key in SLOT_FIELDS:
            _require(key in slot, f"slot lacks {key}")
        _require(bool(SAFE.fullmatch(str(slot["slot"]))), f"unsafe slot id {slot['slot']}")
        _require(slot["slot"] not in seen, f"duplicate slot {slot['slot']}")
        seen.add(slot["slot"])
        _require(slot["set"] in SETS, f"{slot['slot']}: set must be one of {SETS}")
        _require(
            slot["block"] == block_name(slot["set"], int(slot["run"]))
            and int(slot["run"]) in range(1, RUNS_PER_PAIR + 1),
            f"{slot['slot']}: block must be <set>-r<run>",
        )
        _require(
            slot["slot"] == slot_id(slot["set"], int(slot["pair"]), int(slot["run"])),
            f"{slot['slot']}: slot id must be set:pair:r<run>",
        )
        _require(slot["kind"] in ("mutant", "null"), f"{slot['slot']}: kind")
        _require(bool(HEX64.fullmatch(str(slot["candidate_sha256"]))), "candidate_sha256")
        task = slot["task_id"]
        split = "dev" if purpose == "development" else "confirm"
        _require(task in set(splits[split]), f"{slot['slot']}: {task} is not a {split} task")
        files = slot["files"]
        _require(isinstance(files, dict) and bool(files), f"{slot['slot']}: files")
        target = False
        for vm_path, entry in files.items():
            _require(str(vm_path).startswith("/"), f"{slot['slot']}: {vm_path} is not absolute")
            _require(entry.get("root") in ROOTS, f"{slot['slot']}: unknown root")
            rel = str(entry.get("rel", ""))
            _require(
                bool(rel) and not rel.startswith("/") and ".." not in Path(rel).parts,
                f"{slot['slot']}: unsafe rel path",
            )
            _require(bool(HEX64.fullmatch(str(entry.get("sha256")))), f"{slot['slot']}: sha256")
            if entry["root"] == "file_cache":
                _require(
                    receipts.get(rel) == entry["sha256"],
                    f"{slot['slot']}: {rel} differs from the file cache receipts",
                )
            else:
                _require(
                    rel.startswith(f"{slot['mutant_id']}/"),
                    f"{slot['slot']}: a candidate file outside its mutant's directory",
                )
                target |= entry["sha256"] == slot["candidate_sha256"]
        _require(target, f"{slot['slot']}: no candidate file carries candidate_sha256")
    if purpose == "development":
        _require("dev" in run_name, "a development job injects a dev-split mutation run")
    else:
        check_registered(m, source_dir)
    return m


def check_registered(m: Mapping[str, Any], source_dir: Path) -> None:
    """Purpose k2: the registered settings and exactly the registered slots (section 4)."""
    for key, value in REGISTERED_SETTINGS.items():
        _require(m.get(key, value) == value, f"{key} is fixed at {value} for the k2 job")
    _require(
        m["vm"]["concurrency"] == REGISTERED_CONCURRENCY,
        f"the k2 job runs at V = {REGISTERED_CONCURRENCY}",
    )
    _require(
        m.get("slurm") == REGISTERED_SLURM, f"the k2 job's Slurm request is {REGISTERED_SLURM}"
    )
    _require(
        m["candidates"]["run"] == REGISTERED_CANDIDATES_RUN,
        f"the k2 job injects {REGISTERED_CANDIDATES_RUN}",
    )
    _require(
        m.get("jobs_sha256") == REGISTERED_JOBS_SHA256,
        "the k2 job's slots are rendered from the pinned scoring-jobs.jsonl (jobs_sha256)",
    )
    expected = expand_runs(registered_pairs(source_dir))
    got = [{k: s[k] for k in ("slot", *IDENTITY_FIELDS)} for s in m["slots"]]
    want = [{k: s[k] for k in ("slot", *IDENTITY_FIELDS)} for s in expected]
    _require(got == want, "the k2 job's slots differ from the registered slots")


# --------------------------------------------------------------------------- host checks


def check_host(m: Mapping[str, Any]) -> dict[str, Any]:
    """Host inputs exist and match the manifest (run on the host before submitting)."""
    out = s1a.check_host(m)
    root = Path(m["candidates"]["host_dir"])
    cache = Path(m["file_cache"]["host_dir"])
    hashed = 0
    for slot in m["slots"]:
        if slot["run"] != 1:
            continue
        for entry in slot["files"].values():
            base = root if entry["root"] == "candidates" else cache
            path = base / entry["rel"]
            _require(path.is_file() and not path.is_symlink(), f"{path} is missing")
            _require(sha256_file(path) == entry["sha256"], f"{path} differs from the manifest")
            hashed += 1
    out["candidate_files_hashed"] = hashed
    return out


def check_slurm(m: Mapping[str, Any]) -> dict[str, int]:
    slurm = m.get("slurm") or {}
    cpus, memory, minutes = slurm.get("cpus"), slurm.get("memory_gb"), slurm.get("minutes")
    v, cores = m["vm"]["concurrency"], m["vm"]["cpu_cores"]
    need = v * cores + max(1, (v + 1) // 2)
    _require(isinstance(cpus, int) and not isinstance(cpus, bool), "slurm.cpus must be an int")
    _require(
        need <= cpus <= v * cores + v + 8,
        f"slurm.cpus must be {need}-{v * cores + v + 8} at V = {v}",
    )
    _require(isinstance(memory, int) and memory >= 7 * v + 6, "slurm.memory_gb too small")
    _require(isinstance(minutes, int) and 1 <= minutes <= 720, "slurm.minutes 1-720")
    return {"cpus": cpus, "memory_gb": memory, "minutes": minutes}


# --------------------------------------------------------------------------- the lane


def episode_argv(
    cfg: s1a.LaneConfig, name: str, vm: str, out_dir: Path, cpuset: str | None
) -> list[str]:
    m = cfg.manifest
    argv = [
        "docker",
        "run",
        "--rm",
        "--name",
        name,
        "--label",
        f"cotcodec.slurm_job={cfg.job_id}",
        "--label",
        "cotcodec.q2mk2=1",
        "--label",
        "cotcodec.role=episode",
        "--runtime",
        "runc",
        "--network",
        f"container:{vm}",
        "--user",
        f"{cfg.uid}:{cfg.gid}",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,size=2g",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "6g",
        "--pids-limit",
        "2048",
        "--env",
        "CUDA_VISIBLE_DEVICES=",
        "--env",
        "NVIDIA_VISIBLE_DEVICES=void",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "HOME=/tmp/home",
        "--env",
        "MPLCONFIGDIR=/tmp/mpl",
        "--env",
        "XDG_CACHE_HOME=/tmp/cache",
        "--volume",
        f"{cfg.source_dir}:/src:ro",
        "--volume",
        f"{m['osworld']['host_dir']}:/inputs/OSWorld:ro",
        "--volume",
        f"{m['file_cache']['host_dir']}:{ROOTS['file_cache']}:ro",
        "--volume",
        f"{m['candidates']['host_dir']}:{ROOTS['candidates']}:ro",
        "--volume",
        f"{out_dir}:/out",
        "--workdir",
        "/src",
    ]
    if cpuset:
        argv += ["--cpuset-cpus", cpuset]
    argv += [
        m["episode_image_id"],
        m.get("episode_python", "/opt/venv-lock/bin/python"),
        "-m",
        "harness.q2_mutation_k2.executor",
        "--config",
        "/out/config.json",
    ]
    return argv


class K2Lane(s1a.Lane):
    """The S1a lane with K2 slots, the K2 executor and K2 records."""

    def __init__(self, cfg: s1a.LaneConfig, **kwargs: Any):
        kwargs.setdefault("certified", [])
        super().__init__(cfg, **kwargs)

    def episode_config(self, slot: s1a.Slot, out_dir: Path, t_vm_start: float) -> dict:
        d, m = slot.data, self.m
        return {
            "lane": m["name"],
            "purpose": m["purpose"],
            "slot": slot.id,
            "set": d["set"],
            "pair": d["pair"],
            "run": d["run"],
            "attempt": slot.attempt,
            "block": d["block"],
            "job_id": d["job_id"],
            "mutant_id": d["mutant_id"],
            "task_id": d["task_id"],
            "kind": d["kind"],
            "candidate_sha256": d["candidate_sha256"],
            "files": {
                p: {"local": container_path(e), "sha256": e["sha256"]}
                for p, e in d["files"].items()
            },
            "out_dir": "/out",
            "guest_ip": m["vm"]["guest_ip"],
            "server_port": m["vm"]["server_port"],
            "osworld_dir": "/inputs/OSWorld",
            "file_cache_dir": ROOTS["file_cache"],
            "settle_after_reset_s": m.get(
                "settle_after_reset_s", REGISTERED_SETTINGS["settle_after_reset_s"]
            ),
            "settle_before_eval_s": m.get(
                "settle_before_eval_s", REGISTERED_SETTINGS["settle_before_eval_s"]
            ),
            "t_vm_start": t_vm_start,
        }

    def run_slot(self, slot: s1a.Slot, worker: int, cycle: int) -> dict[str, Any]:
        from harness.q2.vm.driver import vm_name, vm_run_argv

        cpus = (
            self.cpusets[worker] if self.cpusets else {"vm": None, "vm_mems": None, "runner": None}
        )
        name = vm_name(self.cfg.job_id, cycle)
        episode_name = f"cotcodec-q2mk2-{self.cfg.job_id}-e{cycle:03d}"
        out_dir = self.cfg.run_dir / "runs" / f"{slot.id.replace(':', '_')}.a{slot.attempt}"
        out_dir.mkdir(parents=True, exist_ok=True)
        t_dispatch = self.clock()
        if self.first_dispatch is None:
            self.first_dispatch = t_dispatch
        host: dict[str, Any] = {
            "t_dispatch": t_dispatch,
            "vm": name,
            "worker": worker,
            "cpus": cpus,
        }
        record: dict[str, Any] | None = None
        started_vm = False
        try:
            view = {"campaign_id": f"q2mk2-{self.m['name']}", "vm": self.m["vm"]}
            argv = vm_run_argv(view, self.cfg.job_id, cycle, cpus["vm"], cpus["vm_mems"])
            t_vm = self.clock()
            try:
                started_vm = True
                self.docker.start_vm(argv)
            except Exception as exc:  # noqa: BLE001 - a VM that will not start is cause (4)
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

    def episode(
        self,
        slot: s1a.Slot,
        out_dir: Path,
        t_vm: float,
        episode_name: str,
        vm: str,
        cpus: Mapping[str, Any],
        host: dict[str, Any],
    ) -> dict[str, Any]:
        config = self.episode_config(slot, out_dir, t_vm)
        (out_dir / "config.json").write_text(json.dumps(config, indent=1), encoding="utf-8")
        argv = episode_argv(self.cfg, episode_name, vm, out_dir, cpus["runner"])
        timeout = float(self.m.get("episode_timeout_s", REGISTERED_SETTINGS["episode_timeout_s"]))
        rc = self.docker.run_episode(
            argv, episode_name, timeout, self.stop, out_dir / "container.log"
        )
        host["episode_rc"] = rc
        path = out_dir / "k2-run.json"
        if rc is None:
            if self.stop.is_set():
                return self.truncated(slot, "cut at the stop signal")
            return self.loss(slot, "runner_crash", f"run exceeded {timeout} s")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return self.loss(slot, "runner_crash", f"episode container exited {rc}")

    def base_record(self, slot: s1a.Slot) -> dict[str, Any]:
        d = slot.data
        return {
            "schema": RUN_SCHEMA,
            "experiment_id": EXPERIMENT_ID,
            "lane": self.m["name"],
            "purpose": self.m["purpose"],
            "slot": slot.id,
            "set": d["set"],
            "pair": d["pair"],
            "run": d["run"],
            "attempt": slot.attempt,
            "block": d["block"],
            "job_id": d["job_id"],
            "mutant_id": d["mutant_id"],
            "task_id": d["task_id"],
            "kind": d["kind"],
            "candidate_sha256": d["candidate_sha256"],
            "score": None,
            "verdict": None,
        }

    def loss(self, slot: s1a.Slot, kind: str, detail: str) -> dict[str, Any]:
        return {
            **self.base_record(slot),
            "status": "infrastructure",
            "exclusion": "vm_infrastructure_failure",
            "infrastructure_type": kind,
            "infrastructure_detail": detail[:500],
        }

    def truncated(self, slot: s1a.Slot, detail: str) -> dict[str, Any]:
        return {
            **self.base_record(slot),
            "status": "cap_truncated",
            "exclusion": None,
            "infrastructure_type": None,
            "cap_detail": detail,
        }

    def records_name(self) -> str:
        return "k2-runs.jsonl"

    def write_receipt(self, receipt: Mapping[str, Any]) -> None:
        out = dict(receipt)
        out["schema"] = "q2m-k2-lane-receipt-v1"
        out["experiment_id"] = EXPERIMENT_ID
        out["identity"] = identity(self.cfg.source_dir, self.m)
        super().write_receipt(out)


def identity(source_dir: Path, m: Mapping[str, Any]) -> dict[str, Any]:
    """What the K2 report records as the executor before any comparison (parent section 10):
    the exported tree's commit and digest, the freeze it holds (the export's own ledger row:
    for the k2 job the commit is the freeze commit, whose parent is the row's
    ``git_head_at_freeze``), the VM image and disk, the episode image."""
    sha = source_dir / ".git_sha"
    row = ledger_row(source_dir)
    return {
        "executor_commit": sha.read_text(encoding="utf-8").strip() if sha.is_file() else None,
        "git_head_at_freeze": row.get("git_head_at_freeze") if row else None,
        "ledger_row_hash": row.get("hash") if row else None,
        "registration_sha256": row.get("sha256") if row else None,
        "source_tree_sha256": tree_sha256(source_dir),
        "vm_image": m["vm"]["image"],
        "vm_image_id": m["vm"]["image_id"],
        "qcow2_sha256": m["vm"]["qcow2"]["sha256"],
        "episode_image_id": m["episode_image_id"],
        "osworld_commit": m["osworld"]["commit"],
        "candidates_run": m["candidates"]["run"],
    }


def tree_sha256(source_dir: Path) -> str:
    return s1a.tree_sha256(source_dir)


# --------------------------------------------------------------------------- submit


def canonical(manifest: Mapping[str, Any]) -> str:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def prior_k2_runs(run_root: Path, exclude: Path | None = None) -> list[str]:
    """Run directories under ``run_root`` whose job started as this id's ``k2`` job (the batch
    file writes ``manifest.json`` before the lane starts), other than ``exclude``; a directory
    whose run refused itself (``refused.json``) never started a VM and does not count."""
    out = []
    if not run_root.is_dir():
        return out
    for run_dir in sorted(p for p in run_root.iterdir() if p.is_dir()):
        if exclude is not None and run_dir.resolve() == exclude.resolve():
            continue
        if (run_dir / REFUSED).exists():
            continue
        for name in ("manifest.json", "lane-receipt.json"):
            path = run_dir / name
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                out.append(run_dir.name)  # unreadable: fail closed
                break
            if data.get("purpose") == "k2" and data.get("experiment_id", EXPERIMENT_ID) == (
                EXPERIMENT_ID
            ):
                out.append(run_dir.name)
                break
    return out


def check_one_job(m: Mapping[str, Any], run_dir: Path | None = None) -> None:
    """Section 4's "one job": a second k2 job is refused at submission and at its start."""
    if m["purpose"] != "k2":
        return
    prior = prior_k2_runs(Path(m["run_root"]), exclude=run_dir)
    _require(
        not prior,
        f"a k2 job already ran under the run root ({prior}); it is rerun only under section "
        "6's repair rule, with its own experiment id",
    )


def submit(manifest_path: Path, source_dir: Path, dry_run: bool) -> dict[str, Any]:
    m = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")), source_dir)
    check_one_job(m)
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
        "COTCODEC_K2_MANIFEST_PATH_HEX": str(stored).encode().hex(),
        "COTCODEC_K2_MANIFEST_SHA256": digest,
        "COTCODEC_BATCH_SHA256": sha256_file(batch),
        "COTCODEC_SOURCE_HOST_HEX": str(source_dir.resolve()).encode().hex(),
        "COTCODEC_SOURCE_TREE_SHA256": tree_sha256(source_dir),
        "COTCODEC_RUN_ROOT_HEX": str(run_root).encode().hex(),
    }
    hours, mins = divmod(request["minutes"], 60)
    argv = [
        "sbatch",
        "--parsable",
        f"--cpus-per-task={request['cpus']}",
        f"--mem={request['memory_gb']}G",
        f"--time={hours:02d}:{mins:02d}:00",
        f"--job-name=q2mk2-{m['name']}"[:60],
        "--export=ALL," + ",".join(f"{k}={v}" for k, v in env.items()),
        str(batch),
    ]
    out = {"manifest_sha256": digest, "manifest": str(stored), "host": host, "argv": argv}
    if not dry_run:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=True)
        out["job_id"] = done.stdout.strip()
    return out


def check_job_list(purpose: str, sample: Path, jobs: Path, summary: Path | None) -> dict[str, str]:
    """The job list the slots are mapped from is the one the sample was drawn from: its
    SHA-256 equals the sample summary's ``jobs_sha256`` (and, for the k2 job, the registered
    one), and the sample's equals the summary's ``sample_sha256``."""
    digests = {"sample_sha256": sha256_file(sample), "jobs_sha256": sha256_file(jobs)}
    if purpose == "k2":
        _require(
            digests["jobs_sha256"] == REGISTERED_JOBS_SHA256,
            f"{jobs} is not the pinned scoring-jobs.jsonl ({digests['jobs_sha256']})",
        )
        _require(
            digests["sample_sha256"] == REGISTERED_SAMPLE_SHA256,
            "the K2 sample is not the frozen sample",
        )
    if summary is not None:
        drawn = json.loads(summary.read_text(encoding="utf-8"))
        for key, value in digests.items():
            _require(drawn.get(key) == value, f"{key} differs from {summary}")
    elif purpose != "k2":
        raise LaneError("a development render names the sample's summary (--sample-summary)")
    return digests


def render(args: argparse.Namespace) -> dict[str, Any]:
    """A manifest from a sample (and an optional candidate list) and the mutation run's job
    list, with every candidate file hashed on the host."""
    base = json.loads(Path(args.base).read_text(encoding="utf-8"))
    digests = check_job_list(
        str(base.get("purpose")), Path(args.sample), Path(args.jobs), args.sample_summary
    )
    base["jobs_sha256"] = digests["jobs_sha256"]
    pairs = [
        {"set": "k2", "pair": i, **_identity(r)} for i, r in enumerate(read_jsonl(args.sample))
    ]
    if args.k2c:
        pairs += [
            {"set": "k2c", "pair": i, **_identity(r)} for i, r in enumerate(read_jsonl(args.k2c))
        ]
    if args.only:
        wanted = set(args.only.split(","))
        pairs = [p for p in pairs if f"{p['set']}:{p['pair']:03d}" in wanted]
    jobs = {j["job_id"]: j for j in read_jsonl(Path(args.jobs))}
    roots = {"candidates": args.build_prefix, "file_cache": args.cache_prefix}
    host_roots = {
        "candidates": Path(base["candidates"]["host_dir"]),
        "file_cache": Path(base["file_cache"]["host_dir"]),
    }
    base["slots"] = render_slots(pairs, jobs, roots=roots, host_roots=host_roots)
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run a validated manifest (inside q2m-k2-vm.sbatch)")
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
    rend = sub.add_parser("render", help="render a manifest's slots (on the host)")
    rend.add_argument("--base", required=True, help="manifest without slots (JSON)")
    rend.add_argument("--sample", type=Path, required=True, help="k2-sample.jsonl")
    rend.add_argument("--k2c", type=Path, default=None, help="K2-C candidate list (JSONL)")
    rend.add_argument("--only", default=None, help="comma-separated set:pair ids (development)")
    rend.add_argument("--jobs", required=True, help="the mutation run's build/scoring-jobs.jsonl")
    rend.add_argument(
        "--sample-summary",
        type=Path,
        default=None,
        help="the sample's k2-sample.summary.json (jobs_sha256, sample_sha256)",
    )
    rend.add_argument("--build-prefix", default="/out/files")
    rend.add_argument("--cache-prefix", default="/inputs/file_cache_1e112283/files")
    rend.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "render":
        manifest = render(args)
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
    try:
        check_one_job(manifest, args.run_dir)
    except LaneError as exc:
        # Recorded so that this directory, which started no VM, never counts as a k2 run.
        (args.run_dir / REFUSED).write_text(json.dumps({"refused": str(exc)}), encoding="utf-8")
        raise SystemExit(f"refused: {exc}") from exc
    from harness.q2.vm.driver import slurm_cpu_ids, snapshot_host

    cpusets = s1a.plan_cpusets(
        slurm_cpu_ids(args.job_id), manifest["vm"]["concurrency"], manifest["vm"]["cpu_cores"]
    )
    k2 = K2Lane(
        s1a.LaneConfig(manifest, args.job_id, args.run_dir, args.source_dir),
        cpusets=cpusets,
        snapshot=snapshot_host,
    )
    signal.signal(signal.SIGUSR1, lambda *_: k2.stop.set())
    receipt = k2.run()
    print(json.dumps({k: receipt[k] for k in ("records", "statuses", "stopped")}))
    return 0 if "error" not in receipt else 3


if __name__ == "__main__":
    raise SystemExit(main())
