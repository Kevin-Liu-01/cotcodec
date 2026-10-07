"""Validate VM campaign manifests (decision D12: CPU-only Slurm jobs, GPU-less containers).

A VM campaign is a Slurm job that requests no GPU, starts digest-pinned
OSWorld desktop VM containers and GPU-less runner containers, and cleans up
only the containers it labelled. The same validator runs on the submitter side
(``scripts/submit_vm_campaign.py``) and again inside the batch job (the host
driver re-validates the decoded manifest before touching Docker), so a manifest
that drifts between submission and execution fails closed.

Standard library only; Python 3.10 compatible.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
from pathlib import PurePosixPath
from typing import Any

SCHEMA = "cotcodec-vm-campaign-v1"
RUN_ROOT_PREFIX = PurePosixPath("/home/kevin/cotcodec-runs")
# Another agent's dirty checkout; nothing here may point into it.
FORBIDDEN_PREFIXES = (PurePosixPath("/home/kevin/cotcodec"),)
HOST_CPUS = 208
MAX_CONCURRENCY = 40
VM_GUEST_NET = ipaddress.ip_network("20.20.20.0/24")
GUEST_SERVER_PORT = 5000
HMP_PORT = 7100

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
CAMPAIGN_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{2,63}$")
EXPERIMENT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,79}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_REF_RE = re.compile(r"^[a-z0-9][a-z0-9./_-]{0,127}@sha256:[0-9a-f]{64}$")
PATH_RE = re.compile(r"^/[A-Za-z0-9._/-]{1,511}$")
REPO_PATH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,255}$")
SIZE_G_RE = re.compile(r"^[1-9][0-9]{0,2}G$")
CPUSET_RE = re.compile(r"^[0-9]{1,3}(-[0-9]{1,3})?(,[0-9]{1,3}(-[0-9]{1,3})?)*$")
HF_URL_RE = re.compile(
    r"^https://huggingface\.co/datasets/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/resolve/"
    r"(?P<rev>[0-9a-f]{40})/[A-Za-z0-9_./-]+$"
)
LICENSE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,63}$")
SEED_FLAG_RE = re.compile(r"^--[a-z][a-z0-9-]{0,31}$")

PURPOSES = ("infrastructure-validation", "reference-capture", "development", "acceptance")
NETWORKS = ("none-netns", "bridge-unpublished")
CONTAINER_PROFILES = ("default", "large-cpu-mem")
WORKLOAD_KINDS = (
    "boot-reset-validation",
    "rdev-capture",
    "inputs-validation",
    "suite-development",
    "canary-development",
)
# Development runs the Stage-1 executor and harnesses only. L0-raw (validity control
# C2) and the detection controls (C1) are scored once on frozen code, never in
# development, so they are not admitted here.
DEVELOPMENT_LAYERS = ("L0-fixed", "H-OSW-fixed", "H-GA")
DEVELOPMENT_SEED = 42
ACCEPTANCE_SEEDS = (43, 44)
SETTINGS = ("screenshot", "screenshot+a11y")
CANARY_APPS = ("writer", "chrome", "vscode", "terminal")
GPU_WORDS = ("gpu", "gpus", "gres", "nvidia", "cuda")


class ManifestError(ValueError):
    """Raised when a VM campaign manifest is not admissible."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def manifest_sha256(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()


def source_tree_sha256(source_dir: str, subdir: str = "harness") -> str:
    """Digest of every regular file under ``source_dir/subdir`` (bytecode excluded).

    One line per file, sorted by relative path: ``<relpath>\\0<sha256>\\n``.
    The batch script recomputes this inline; tests keep the two in step.
    """
    root = os.path.join(source_dir, subdir)
    if not os.path.isdir(root) or os.path.islink(root):
        raise ManifestError(f"source subtree {subdir!r} is missing or a symlink")
    entries: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for filename in filenames:
            if filename.endswith((".pyc", ".pyo")):
                continue
            path = os.path.join(dirpath, filename)
            if os.path.islink(path):
                raise ManifestError(f"source tree contains a symlink: {path}")
            relative = os.path.relpath(path, source_dir).replace(os.sep, "/")
            digest = hashlib.sha256()
            with open(path, "rb") as handle:
                for chunk in iter(lambda h=handle: h.read(1 << 20), b""):
                    digest.update(chunk)
            entries.append((relative, digest.hexdigest()))
    entries.sort()
    outer = hashlib.sha256()
    for relative, digest_hex in entries:
        outer.update(f"{relative}\0{digest_hex}\n".encode())
    return outer.hexdigest()


def _require_keys(obj: Any, where: str, required: set[str], optional: set[str] = frozenset()):
    if not isinstance(obj, dict):
        raise ManifestError(f"{where} must be a mapping")
    keys = set(obj)
    missing = required - keys
    unknown = keys - required - set(optional)
    if missing:
        raise ManifestError(f"{where} is missing {sorted(missing)}")
    if unknown:
        raise ManifestError(f"{where} has unknown keys {sorted(unknown)}")
    return obj


def _no_gpu_words(value: Any, where: str = "manifest") -> None:
    """Reject any key that would request or mention GPUs (fail closed, recursively)."""
    if isinstance(value, dict):
        for key, inner in value.items():
            lowered = str(key).lower()
            if any(word in lowered for word in GPU_WORDS):
                raise ManifestError(f"{where}.{key}: VM campaigns may not request GPUs")
            _no_gpu_words(inner, f"{where}.{key}")
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            _no_gpu_words(inner, f"{where}[{index}]")


def _host_path(value: Any, where: str) -> str:
    if not isinstance(value, str) or not PATH_RE.fullmatch(value):
        raise ManifestError(f"{where} must be an absolute path with safe characters")
    path = PurePosixPath(value)
    if ".." in path.parts:
        raise ManifestError(f"{where} contains traversal")
    if path != RUN_ROOT_PREFIX and RUN_ROOT_PREFIX not in path.parents:
        raise ManifestError(f"{where} must live under {RUN_ROOT_PREFIX}")
    for forbidden in FORBIDDEN_PREFIXES:
        if path == forbidden or forbidden in path.parents:
            raise ManifestError(f"{where} points into a forbidden checkout")
    return value


def _int(value: Any, where: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ManifestError(f"{where} must be an integer in [{low}, {high}]")
    return value


def _bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise ManifestError(f"{where} must be a boolean")
    return value


def _match(value: Any, pattern: re.Pattern[str], where: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ManifestError(f"{where} has an invalid value")
    return value


def parse_cpuset(spec: str) -> list[int]:
    if not CPUSET_RE.fullmatch(spec):
        raise ManifestError("cpuset must look like '0-7,16'")
    cpus: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            low_s, high_s = part.split("-", 1)
            low, high = int(low_s), int(high_s)
            if high < low:
                raise ManifestError("cpuset range is reversed")
            cpus.extend(range(low, high + 1))
        else:
            cpus.append(int(part))
    if len(set(cpus)) != len(cpus):
        raise ManifestError("cpuset lists a CPU twice")
    if any(cpu >= HOST_CPUS for cpu in cpus):
        raise ManifestError(f"cpuset names a CPU outside 0-{HOST_CPUS - 1}")
    return sorted(cpus)


def _gib(size: str) -> int:
    return int(size[:-1])


def validate_manifest(raw: Any) -> dict[str, Any]:
    """Return the manifest unchanged if admissible, else raise ManifestError."""
    _no_gpu_words(raw)
    manifest = _require_keys(
        raw,
        "manifest",
        {
            "schema",
            "name",
            "campaign_id",
            "experiment_id",
            "purpose",
            "preregistration",
            "git_sha",
            "source",
            "run_root",
            "slurm",
            "container_profile",
            "model",
            "randomness",
            "vm",
            "runner",
            "workload",
        },
    )
    if manifest["schema"] != SCHEMA:
        raise ManifestError(f"schema must be {SCHEMA}")
    _match(manifest["name"], NAME_RE, "name")
    _match(manifest["campaign_id"], CAMPAIGN_RE, "campaign_id")
    _match(manifest["experiment_id"], EXPERIMENT_RE, "experiment_id")
    purpose = manifest["purpose"]
    if purpose not in PURPOSES:
        raise ManifestError(f"purpose must be one of {PURPOSES}")
    _match(manifest["git_sha"], GIT_RE, "git_sha")

    prereg = _require_keys(
        manifest["preregistration"], "preregistration", {"path", "status", "sha256"}
    )
    _match(prereg["path"], REPO_PATH_RE, "preregistration.path")
    if not prereg["path"].startswith("program/preregistrations/") or ".." in prereg["path"]:
        raise ManifestError("preregistration.path must be under program/preregistrations/")
    if prereg["status"] not in ("absent", "draft", "frozen"):
        raise ManifestError("preregistration.status must be absent, draft or frozen")
    if prereg["status"] == "absent":
        # Infrastructure validation may precede the preregistration text.
        if purpose != "infrastructure-validation" or prereg["sha256"] is not None:
            raise ManifestError("only infrastructure validation may run without a preregistration")
    else:
        _match(prereg["sha256"], SHA_RE, "preregistration.sha256")
    if purpose == "acceptance":
        # Confirmatory trials (A1-A6, and the scored controls C1-C3) wait for the
        # owner's freeze of the main preregistration and of both addenda
        # (q2-action-path-v1-inputs and q2-action-path-v1-executor). Until a
        # reviewed change after that freeze admits them with a ledger check,
        # every acceptance manifest is refused (gauntlet rule 3).
        if prereg["status"] != "frozen":
            raise ManifestError("acceptance campaigns require a frozen preregistration")
        raise ManifestError(
            "acceptance is refused until the preregistration and both addenda are frozen"
        )

    source = _require_keys(manifest["source"], "source", {"host_dir", "tree_sha256"})
    _host_path(source["host_dir"], "source.host_dir")
    if PurePosixPath(source["host_dir"]).name != manifest["git_sha"]:
        raise ManifestError("source.host_dir must end in the exported git_sha")
    _match(source["tree_sha256"], SHA_RE, "source.tree_sha256")
    _host_path(manifest["run_root"], "run_root")

    slurm = _require_keys(manifest["slurm"], "slurm", {"cpus", "memory_gb", "minutes"})
    _int(slurm["cpus"], "slurm.cpus", 1, HOST_CPUS)
    _int(slurm["memory_gb"], "slurm.memory_gb", 2, 1024)
    _int(slurm["minutes"], "slurm.minutes", 5, 1440)

    if manifest["container_profile"] not in CONTAINER_PROFILES:
        raise ManifestError(f"container_profile must be one of {CONTAINER_PROFILES}")
    model = _require_keys(manifest["model"], "model", {"kind", "reason"})
    if model["kind"] != "none":
        raise ManifestError("VM campaigns load no model weights (model.kind must be none)")
    if not isinstance(model["reason"], str) or not 10 <= len(model["reason"]) <= 300:
        raise ManifestError("model.reason must explain why no model is used")

    randomness = _require_keys(
        manifest["randomness"], "randomness", {"contract", "seeds"}, {"seed_binding"}
    )
    seeds = randomness["seeds"]
    if not isinstance(seeds, list) or any(
        isinstance(s, bool) or not isinstance(s, int) or s < 0 for s in seeds
    ):
        raise ManifestError("randomness.seeds must be a list of non-negative integers")
    if set(seeds) & set(ACCEPTANCE_SEEDS):
        # Seeds 43 and 44 are the preregistered acceptance shuffles; no campaign may
        # use them before the freeze, whatever its stated purpose.
        raise ManifestError("seeds 43 and 44 are reserved for acceptance after the freeze")
    if len(set(seeds)) != len(seeds):
        raise ManifestError("randomness.seeds repeats a seed")
    if randomness["contract"] == "deterministic":
        if seeds or "seed_binding" in randomness:
            raise ManifestError("deterministic campaigns declare no seeds")
    elif randomness["contract"] == "seeded":
        if not seeds:
            raise ManifestError("seeded campaigns must declare their seeds")
        binding = _require_keys(randomness.get("seed_binding"), "randomness.seed_binding", {"flag"})
        _match(binding["flag"], SEED_FLAG_RE, "randomness.seed_binding.flag")
    else:
        raise ManifestError("randomness.contract must be deterministic or seeded")

    vm = _require_keys(
        manifest["vm"],
        "vm",
        {
            "image",
            "image_id",
            "qcow2",
            "ram_size",
            "cpu_cores",
            "disk_size",
            "memory_gb",
            "network",
            "guest_ip",
            "server_port",
            "hmp_port",
            "concurrency",
        },
        {"cpuset_cpus", "cpuset_mems"},
    )
    _match(vm["image"], IMAGE_REF_RE, "vm.image")
    _match(vm["image_id"], IMAGE_ID_RE, "vm.image_id")
    qcow2 = _require_keys(
        vm["qcow2"],
        "vm.qcow2",
        {
            "host_path",
            "sha256",
            "size_bytes",
            "source_url",
            "archive_sha256",
            "revision",
            "license",
        },
    )
    _host_path(qcow2["host_path"], "vm.qcow2.host_path")
    if not qcow2["host_path"].endswith(".qcow2"):
        raise ManifestError("vm.qcow2.host_path must be a .qcow2 file")
    _match(qcow2["sha256"], SHA_RE, "vm.qcow2.sha256")
    _match(qcow2["archive_sha256"], SHA_RE, "vm.qcow2.archive_sha256")
    _int(qcow2["size_bytes"], "vm.qcow2.size_bytes", 1, 1 << 40)
    _match(qcow2["revision"], GIT_RE, "vm.qcow2.revision")
    url_match = HF_URL_RE.fullmatch(str(qcow2["source_url"]))
    if not url_match or url_match.group("rev") != qcow2["revision"]:
        raise ManifestError("vm.qcow2.source_url must be a revision-pinned Hugging Face URL")
    _match(qcow2["license"], LICENSE_RE, "vm.qcow2.license")
    _match(vm["ram_size"], SIZE_G_RE, "vm.ram_size")
    _match(vm["disk_size"], SIZE_G_RE, "vm.disk_size")
    cores = _int(vm["cpu_cores"], "vm.cpu_cores", 1, 16)
    vm_mem = _int(vm["memory_gb"], "vm.memory_gb", 2, 64)
    if vm_mem < _gib(vm["ram_size"]) + 1:
        raise ManifestError("vm.memory_gb must leave at least 1 GiB above the guest RAM")
    if vm["network"] not in NETWORKS:
        raise ManifestError(f"vm.network must be one of {NETWORKS}")
    try:
        guest_ip = ipaddress.ip_address(str(vm["guest_ip"]))
    except ValueError as exc:
        raise ManifestError("vm.guest_ip must be an IPv4 address") from exc
    if guest_ip not in VM_GUEST_NET:
        raise ManifestError(f"vm.guest_ip must be inside the image's NAT net {VM_GUEST_NET}")
    if vm["server_port"] != GUEST_SERVER_PORT or vm["hmp_port"] != HMP_PORT:
        raise ManifestError("guest server and HMP ports are fixed by the pinned image")
    concurrency = _int(vm["concurrency"], "vm.concurrency", 1, MAX_CONCURRENCY)
    if "cpuset_cpus" in vm:
        cpus = parse_cpuset(_match(vm["cpuset_cpus"], CPUSET_RE, "vm.cpuset_cpus"))
        if len(cpus) < cores * concurrency:
            raise ManifestError("vm.cpuset_cpus is smaller than cpu_cores x concurrency")
    if "cpuset_mems" in vm and vm["cpuset_mems"] not in ("0", "1"):
        raise ManifestError("vm.cpuset_mems must be NUMA node 0 or 1")

    runner = _require_keys(manifest["runner"], "runner", {"image_id", "memory_gb", "cpus"})
    _match(runner["image_id"], IMAGE_ID_RE, "runner.image_id")
    runner_mem = _int(runner["memory_gb"], "runner.memory_gb", 1, 16)
    runner_cpus = _int(runner["cpus"], "runner.cpus", 1, 8)

    if slurm["cpus"] < concurrency * cores + runner_cpus:
        raise ManifestError("slurm.cpus must cover concurrency x cpu_cores plus the runner")
    if slurm["memory_gb"] < concurrency * vm_mem + runner_mem + 2:
        raise ManifestError("slurm.memory_gb must cover every VM, the runner and 2 GiB slack")

    workload = manifest["workload"]
    if not isinstance(workload, dict) or workload.get("kind") not in WORKLOAD_KINDS:
        raise ManifestError(f"workload.kind must be one of {WORKLOAD_KINDS}")
    if workload["kind"] == "boot-reset-validation":
        _require_keys(
            workload,
            "workload",
            {
                "kind",
                "cycles",
                "boot_timeout_s",
                "settle_timeout_s",
                "hmp_input_check",
                "latency_reps",
                "exposure_probe",
            },
            {"tap_selftest"},
        )
        cycles = _int(workload["cycles"], "workload.cycles", 1, 60)
        if "tap_selftest" in workload:
            _bool(workload["tap_selftest"], "workload.tap_selftest")
        boot_timeout = _int(workload["boot_timeout_s"], "workload.boot_timeout_s", 60, 900)
        settle_timeout = _int(workload["settle_timeout_s"], "workload.settle_timeout_s", 0, 300)
        _bool(workload["hmp_input_check"], "workload.hmp_input_check")
        _int(workload["latency_reps"], "workload.latency_reps", 0, 20)
        exposure = _bool(workload["exposure_probe"], "workload.exposure_probe")
        if exposure and vm["network"] != "bridge-unpublished":
            raise ManifestError("the exposure probe only applies to bridge-unpublished VMs")
        if concurrency != 1:
            raise ManifestError("boot-reset validation runs one VM at a time")
        if purpose != "infrastructure-validation":
            raise ManifestError("boot-reset validation is infrastructure validation")
        if randomness["contract"] != "deterministic":
            raise ManifestError("boot-reset validation is deterministic")
        # Per cycle: boot, settle, about two minutes of probes, teardown.
        budget = 600 + cycles * (boot_timeout + settle_timeout + 120)
        if slurm["minutes"] * 60 < budget:
            raise ManifestError("slurm.minutes cannot cover the worst-case cycle budget")
    if workload["kind"] == "rdev-capture":
        _require_keys(
            workload,
            "workload",
            {"kind", "reps", "boot_timeout_s", "settle_timeout_s", "plan_sha256"},
        )
        reps = _int(workload["reps"], "workload.reps", 1, 20)
        boot_timeout = _int(workload["boot_timeout_s"], "workload.boot_timeout_s", 60, 900)
        settle_timeout = _int(workload["settle_timeout_s"], "workload.settle_timeout_s", 0, 300)
        _match(workload["plan_sha256"], SHA_RE, "workload.plan_sha256")
        if purpose != "reference-capture":
            raise ManifestError("an R-dev capture is a reference capture")
        if prereg["status"] == "absent":
            raise ManifestError("a reference capture must name its preregistration draft")
        if concurrency != 1 or randomness["contract"] != "deterministic":
            raise ManifestError("an R-dev capture runs one VM, deterministically")
        # 35 entries x reps x at most 6 s each, plus boot, settle and slack.
        budget = 900 + boot_timeout + settle_timeout + reps * 35 * 6
        if slurm["minutes"] * 60 < budget:
            raise ManifestError("slurm.minutes cannot cover the worst-case capture budget")
    if workload["kind"] in ("inputs-validation", "suite-development", "canary-development"):
        _validate_session_workload(manifest, workload, purpose, prereg, randomness, concurrency)
    return manifest


def _validate_session_workload(
    manifest: dict[str, Any],
    workload: dict[str, Any],
    purpose: str,
    prereg: dict[str, Any],
    randomness: dict[str, Any],
    concurrency: int,
) -> None:
    """Workloads that run cold-booted sessions of the suite (one VM at a time)."""
    kind = workload["kind"]
    common = {"kind", "boot_timeout_s", "settle_timeout_s", "cells_sha256", "sessions", "trials",
              "max_trial_s"}  # fmt: skip
    if kind == "inputs-validation":
        _require_keys(workload, "workload", common | {"reps", "canary_readback", "plan_sha256"})
        if purpose != "infrastructure-validation":
            raise ManifestError("inputs validation is infrastructure validation")
        if randomness["contract"] != "deterministic":
            raise ManifestError("inputs validation is deterministic")
        _int(workload["reps"], "workload.reps", 1, 10)
        _bool(workload["canary_readback"], "workload.canary_readback")
        _match(workload["plan_sha256"], SHA_RE, "workload.plan_sha256")
    else:
        extra = {"layer", "cells", "reps", "settings", "session_trials"}
        if kind == "canary-development":
            extra = {"apps", "entries", "reps", "session_trials", "measure_targets"}
        _require_keys(workload, "workload", common | extra)
        if purpose != "development":
            raise ManifestError(f"{kind} is a development workload")
        if randomness["contract"] != "seeded" or randomness["seeds"] != [DEVELOPMENT_SEED]:
            raise ManifestError("development campaigns use exactly seed 42")
        if randomness["seed_binding"]["flag"] != "--seed":
            raise ManifestError("development campaigns bind their seed with --seed")
        _int(workload["reps"], "workload.reps", 1, 5)
        _int(workload["session_trials"], "workload.session_trials", 1, 60)
        if kind == "suite-development":
            if workload["layer"] not in DEVELOPMENT_LAYERS:
                raise ManifestError(f"workload.layer must be one of {DEVELOPMENT_LAYERS}")
            settings = workload["settings"]
            if not isinstance(settings, list) or not settings or not set(settings) <= set(SETTINGS):
                raise ManifestError(f"workload.settings must be a non-empty subset of {SETTINGS}")
            _cell_list(workload["cells"], "workload.cells")
        else:
            apps = workload["apps"]
            if not isinstance(apps, list) or not apps or not set(apps) <= set(CANARY_APPS):
                raise ManifestError(f"workload.apps must be a non-empty subset of {CANARY_APPS}")
            _cell_list(workload["entries"], "workload.entries")
            _bool(workload["measure_targets"], "workload.measure_targets")
    if prereg["status"] == "absent":
        raise ManifestError(f"{kind} must name its preregistration draft")
    if concurrency != 1:
        raise ManifestError(f"{kind} runs one VM at a time")
    _match(workload["cells_sha256"], SHA_RE, "workload.cells_sha256")
    boot_timeout = _int(workload["boot_timeout_s"], "workload.boot_timeout_s", 60, 900)
    settle_timeout = _int(workload["settle_timeout_s"], "workload.settle_timeout_s", 0, 300)
    sessions = _int(workload["sessions"], "workload.sessions", 1, 200)
    trials = _int(workload["trials"], "workload.trials", 1, 20000)
    max_trial = _int(workload["max_trial_s"], "workload.max_trial_s", 5, 600)
    budget = 600 + sessions * (boot_timeout + settle_timeout + 240) + trials * max_trial
    if manifest["slurm"]["minutes"] * 60 < budget:
        raise ManifestError("slurm.minutes cannot cover the worst-case session budget")


def _cell_list(value: Any, where: str) -> None:
    if value == "all":
        return
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(v, str) and REPO_PATH_RE.fullmatch(v) for v in value)
        or len(set(value)) != len(value)
    ):
        raise ManifestError(f"{where} must be 'all' or a list of distinct cell ids")


def container_labels(
    manifest: dict[str, Any], job_id: str, role: str, cycle: int
) -> dict[str, str]:
    return {
        "cotcodec.q2": "1",
        "cotcodec.campaign": manifest["campaign_id"],
        "cotcodec.slurm_job": job_id,
        "cotcodec.role": role,
        "cotcodec.cycle": str(cycle),
    }
