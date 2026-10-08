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
MUTANT_RE = re.compile(r"^M[0-9]{2}-[a-z0-9-]{3,60}$")

PURPOSES = ("infrastructure-validation", "reference-capture", "development", "acceptance")
NETWORKS = ("none-netns", "bridge-unpublished")
CONTAINER_PROFILES = ("default", "large-cpu-mem")
WORKLOAD_KINDS = (
    "boot-reset-validation",
    "rdev-capture",
    "inputs-validation",
    "suite-development",
    "canary-development",
    "suite-acceptance",
    "canary-acceptance",
)
PREREG_ID = "q2-action-path-v1"
ADDENDA_IDS = {"inputs": "q2-action-path-v1-inputs", "executor": "q2-action-path-v1-executor"}
PREREG_DIR = "program/preregistrations"
# The frozen digest tables of the preregistration and its addenda ("Frozen with this
# file" followed by rows of `path` and `sha256`). Admission checks every listed file of
# the source tree against them (design decision 35).
FROZEN_TABLE_MARKER = "Frozen with this file"
FROZEN_ROW_RE = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$")
# Every file a VM campaign can import or read lives under harness/q2 (plus the package
# root); a campaign that needs the executor addendum must find each of them pinned.
CLOSED_WORLD_ROOTS = ("harness/q2",)
CLOSED_WORLD_FILES = ("harness/__init__.py",)
# Runner CPUs per concurrency (preregistration section 9): half a CPU per concurrent
# runner, at least one, at most MAX_RUNNER_CPUS (development at N = 8 used 4).
MAX_RUNNER_CPUS = 20
# A7, the observation-service campaign (decision D30): repetitions of the gating set G in the
# screenshot-plus-accessibility setting, sized in preregistration section 9.
OBSERVATION_REPS = 360
# What each scored campaign needs frozen in the ledger (preregistration sections 2.2 and 8):
# C2 runs after the inputs addendum; C1, C3 and every acceptance criterion after both.
CRITERIA = {
    # criterion: (layers, seeds, reps, settings, cells, addenda)
    "A1": (("L0-fixed",), (43, 44), (5,), "both", "all", ("inputs", "executor")),
    "A2": (("H-OSW-fixed", "H-GA"), (43,), (5,), "both", "all", ("inputs", "executor")),
    "A3": (("L0-fixed", "H-OSW-fixed", "H-GA"), (43,), (30,), "both", "stress",
           ("inputs", "executor")),
    "A4": (("L0-fixed",), (43,), (1,), "both", "volume", ("inputs", "executor")),
    "A7": (("L0-fixed",), (43,), (OBSERVATION_REPS,), "screenshot+a11y", "gating",
           ("inputs", "executor")),
    "ladder": (("L0-fixed",), (43,), "rung", "both", "all", ("inputs", "executor")),
    "C1": (("H-OSW-up", "H-GA-buggy"), (42,), (5,), "screenshot", "all", ("inputs", "executor")),
    "C2": (("L0-raw",), (42,), (5,), "screenshot", "all", ("inputs",)),
    "C3": (("L0-fixed", "H-OSW-fixed", "H-GA"), (42,), (1,), "screenshot", "all",
           ("inputs", "executor")),
}  # fmt: skip
# The concurrency ladder (preregistration section 9). Rung N repeats the seed-43 order of the
# 100 entries (its first five repetitions are A1's seed-43 shuffle) until each setting has at
# least max(N, 10) sessions, so N VMs are busy at once and the rung has at least 20 cold boots.
LADDER_RUNGS = (8, 16, 24, 32, 40)
LADDER_MIN_BOOTS = 20
CATALOG_ENTRIES = 100
SESSION_TRIALS = 60
# Every other scored campaign runs one VM at a time; A4 and A7 run at N* (1 or a ladder rung).
CONCURRENCY = {"A4": (1, *LADDER_RUNGS), "A7": (1, *LADDER_RUNGS), "ladder": LADDER_RUNGS}


def executor_addendum(attempt: int) -> tuple[str, str]:
    """(experiment id, path) of the executor addendum a repair attempt runs under.

    Attempt 1 runs under ``q2-action-path-v1-executor``; a repair attempt k (section 11)
    under ``q2-action-path-v1-executor-a<k>``, frozen in its own ledger row.
    """
    suffix = "" if attempt == 1 else f"-a{attempt}"
    experiment = f"{ADDENDA_IDS['executor']}{suffix}"
    return experiment, f"{PREREG_DIR}/{experiment}.md"


def runner_cpus(concurrency: int) -> int:
    """The runner CPUs an acceptance campaign at this concurrency must use (section 9)."""
    return max(1, min(MAX_RUNNER_CPUS, -(-concurrency // 2)))


def ladder_reps(concurrency: int) -> int:
    """Repetitions of the seed-43 order at a ladder rung (at least A1's five)."""
    want = max(concurrency, LADDER_MIN_BOOTS // len(SETTINGS))
    reps = 5
    while -(-reps * CATALOG_ENTRIES // SESSION_TRIALS) < want:
        reps += 1
    return reps


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


def ledger_view(source_dir: str, paths: list[str]) -> dict[str, Any]:
    """The frozen rows of ``program/preregistrations/ledger.jsonl`` and the files' digests.

    Verifies the ledger's hash chain the way ``scripts/preregister.py`` writes it
    (each row's ``hash`` is the SHA-256 of its other fields as sorted compact JSON,
    and ``previous_hash`` links the rows); a broken chain raises ManifestError.
    """
    ledger_path = os.path.join(source_dir, "program", "preregistrations", "ledger.jsonl")
    rows: dict[str, dict[str, str]] = {}
    previous = "0" * 64
    if os.path.exists(ledger_path):
        with open(ledger_path, encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                body = {k: v for k, v in row.items() if k != "hash"}
                digest = hashlib.sha256(
                    json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                if row.get("previous_hash") != previous or row.get("hash") != digest:
                    raise ManifestError(f"ledger line {number}: broken hash chain")
                rows[row["experiment_id"]] = {
                    "path": row["path"],
                    "sha256": row["sha256"],
                    "git_head_at_freeze": row.get("git_head_at_freeze"),
                }
                previous = row["hash"]
    files: dict[str, str] = {}
    tables: dict[str, dict[str, str]] = {}

    def digest(path: str) -> None:
        full = os.path.join(source_dir, path)
        if path not in files and os.path.isfile(full) and not os.path.islink(full):
            with open(full, "rb") as handle:
                files[path] = hashlib.sha256(handle.read()).hexdigest()

    for path in paths:
        digest(path)
        if path in files:
            with open(os.path.join(source_dir, path), encoding="utf-8") as handle:
                tables[path] = frozen_table(handle.read())
            for listed in tables[path]:
                digest(listed)
    closed = closed_world(source_dir)
    for path in closed:
        digest(path)
    return {"rows": rows, "files": files, "tables": tables, "closed_world": closed}


def frozen_table(text: str) -> dict[str, str]:
    """The ``path -> sha256`` rows of a registration's "Frozen with this file" table."""
    if FROZEN_TABLE_MARKER not in text:
        return {}
    rows: dict[str, str] = {}
    started = False
    for line in text.split(FROZEN_TABLE_MARKER, 1)[1].splitlines():
        match = FROZEN_ROW_RE.match(line.strip())
        if match:
            rows[match.group(1)] = match.group(2)
            started = True
        elif started and not line.strip():
            break
    return rows


def closed_world(source_dir: str) -> list[str]:
    """Every file under harness/q2 (bytecode and Markdown excluded) and the package root."""
    out = [path for path in CLOSED_WORLD_FILES if os.path.isfile(os.path.join(source_dir, path))]
    for root in CLOSED_WORLD_ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(source_dir, root)):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for filename in filenames:
                if filename.endswith((".pyc", ".pyo", ".md")):
                    continue
                full = os.path.join(dirpath, filename)
                out.append(os.path.relpath(full, source_dir).replace(os.sep, "/"))
    return sorted(out)


def ledger_paths(raw: dict[str, Any]) -> list[str]:
    """The files an acceptance manifest pins (for ``ledger_view``)."""
    paths = [str((raw.get("preregistration") or {}).get("path"))]
    for pin in (raw.get("addenda") or {}).values():
        if isinstance(pin, dict):
            paths.append(str(pin.get("path")))
    return paths


def check_ledger(manifest: dict[str, Any], ledger: dict[str, Any], needed: tuple[str, ...]) -> None:
    """Acceptance admission: the ledger freezes the preregistration and the needed addenda.

    ``ledger`` is ``ledger_view``'s result: the hash-chain-verified rows of
    ``program/preregistrations/ledger.jsonl``, the source tree's file digests, each
    registration's frozen table and the closed-world file list. Every row must match the
    manifest's digest and the file in the source tree; every file a needed registration's
    table lists must hold its frozen digest in the source tree; and a campaign that needs
    the executor addendum must find every file under harness/q2 pinned by one of the
    needed tables (design decision 35). The repair attempt names its executor addendum
    (``executor_addendum``).
    """
    rows, files = ledger.get("rows") or {}, ledger.get("files") or {}
    tables = ledger.get("tables") or {}
    wanted = [(PREREG_ID, manifest["preregistration"])]
    for key in needed:
        pin = manifest["addenda"].get(key)
        if pin is None:
            raise ManifestError(f"this campaign needs the {key} addendum frozen and pinned")
        if key == "executor":
            attempt = int(manifest["workload"].get("attempt", 1))
            experiment, path = executor_addendum(attempt)
            if pin["path"] != path:
                raise ManifestError(f"attempt {attempt} runs under {path}, not {pin['path']}")
            wanted.append((experiment, pin))
        else:
            wanted.append((ADDENDA_IDS[key], pin))
    pinned: dict[str, str] = {}
    for experiment_id, pin in wanted:
        row = rows.get(experiment_id)
        if row is None:
            raise ManifestError(f"{experiment_id} is not frozen in the ledger")
        if row["path"] != pin["path"] or row["sha256"] != pin["sha256"]:
            raise ManifestError(f"{experiment_id}: the manifest and the ledger disagree")
        if files.get(pin["path"]) != pin["sha256"]:
            raise ManifestError(f"{pin['path']} changed after it was frozen")
        table = tables.get(pin["path"]) or {}
        if not table:
            raise ManifestError(f"{pin['path']} has no frozen digest table")
        for path, sha in sorted(table.items()):
            if files.get(path) != sha:
                raise ManifestError(
                    f"{path} in the source tree is not the file {experiment_id} froze"
                )
            pinned[path] = sha
    if "executor" in needed:
        unpinned = [path for path in ledger.get("closed_world") or [] if path not in pinned]
        if unpinned:
            raise ManifestError(f"files no frozen table pins: {unpinned[:5]}")


def validate_manifest(raw: Any, ledger: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the manifest unchanged if admissible, else raise ManifestError.

    Acceptance manifests (A1-A6 and the scored controls) also need ``ledger``
    (see ``check_ledger``); without it, or before the owner's freeze, they are
    refused.
    """
    _no_gpu_words(raw)
    optional = (
        {"addenda"} if isinstance(raw, dict) and raw.get("purpose") == "acceptance" else set()
    )
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
        optional,
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
        # owner's freeze of the main preregistration and of the addenda they need
        # (q2-action-path-v1-inputs, q2-action-path-v1-executor). Admission is a
        # ledger check (check_ledger) made by the submitter and again inside the
        # job; without it every acceptance manifest is refused (gauntlet rule 3).
        if prereg["status"] != "frozen":
            raise ManifestError("acceptance campaigns require a frozen preregistration")
        if ledger is None:
            raise ManifestError(
                "acceptance is refused before the freeze of the preregistration and both addenda"
                " (no ledger check was made)"
            )
        # C2 is scored after the inputs freeze and before the executor freeze, so only the
        # inputs addendum is always present; check_ledger requires each one a campaign needs.
        addenda = _require_keys(manifest.get("addenda"), "addenda", {"inputs"}, {"executor"})
        for key in addenda:
            pin = _require_keys(addenda[key], f"addenda.{key}", {"path", "sha256"})
            _match(pin["path"], REPO_PATH_RE, f"addenda.{key}.path")
            _match(pin["sha256"], SHA_RE, f"addenda.{key}.sha256")

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
    if set(seeds) & set(ACCEPTANCE_SEEDS) and purpose != "acceptance":
        # Seeds 43 and 44 are the preregistered acceptance shuffles: only an acceptance
        # campaign, admitted by the ledger check after the freeze, may use them.
        raise ManifestError("seeds 43 and 44 are reserved for acceptance after the freeze")

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
    runner_cpu_count = _int(runner["cpus"], "runner.cpus", 1, MAX_RUNNER_CPUS)

    if slurm["cpus"] < concurrency * cores + runner_cpu_count:
        raise ManifestError("slurm.cpus must cover concurrency x cpu_cores plus the runner")
    if slurm["memory_gb"] < concurrency * (vm_mem + runner_mem) + 2:
        raise ManifestError("slurm.memory_gb must cover every VM, its runner and 2 GiB slack")

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
    if workload["kind"] in ("suite-acceptance", "canary-acceptance"):
        needed = _validate_acceptance_workload(manifest, workload, purpose, randomness)
        assert ledger is not None  # purpose acceptance was checked above
        check_ledger(manifest, ledger, needed)
    elif purpose == "acceptance":
        raise ManifestError("acceptance campaigns use an acceptance workload")
    return manifest


def _validate_acceptance_workload(
    manifest: dict[str, Any],
    workload: dict[str, Any],
    purpose: str,
    randomness: dict[str, Any],
) -> tuple[str, ...]:
    """Fixed shape of each preregistered campaign; returns the addenda it needs frozen."""
    if purpose != "acceptance":
        raise ManifestError(f"{workload['kind']} is an acceptance workload")
    common = {"kind", "boot_timeout_s", "settle_timeout_s", "cells_sha256", "sessions", "trials",
              "max_trial_s", "attempt", "session_trials"}  # fmt: skip
    seeds = randomness["seeds"]
    if randomness["contract"] != "seeded" or len(seeds) != 1:
        raise ManifestError("an acceptance campaign declares exactly one seed")
    if workload["kind"] == "canary-acceptance":
        _require_keys(workload, "workload", common | {"apps", "reps"})
        if seeds != [43] or workload["reps"] != 5 or workload["apps"] != list(CANARY_APPS):
            raise ManifestError("A6 runs every app, 5 repetitions, in the seed-43 order")
        if manifest["vm"]["concurrency"] != 1:
            raise ManifestError("A6 runs one VM at a time")
        needed: tuple[str, ...] = ("inputs", "executor")
    else:
        _require_keys(
            workload, "workload",
            common | {"criterion", "layer", "reps", "settings", "cells", "mutant", "session_range"},
        )  # fmt: skip
        criterion = workload["criterion"]
        if criterion not in CRITERIA:
            raise ManifestError(f"workload.criterion must be one of {sorted(CRITERIA)}")
        layers, allowed_seeds, reps, settings, cells, needed = CRITERIA[criterion]
        if workload["layer"] not in layers or seeds[0] not in allowed_seeds:
            raise ManifestError(f"{criterion}: layer or seed outside the preregistration")
        concurrency = manifest["vm"]["concurrency"]
        if concurrency not in CONCURRENCY.get(criterion, (1,)):
            raise ManifestError(f"{criterion} cannot run at concurrency {concurrency}")
        if reps == "rung":
            reps = (ladder_reps(concurrency),)
        if workload["reps"] not in reps:
            raise ManifestError(f"{criterion}: repetitions outside the preregistration")
        want = list(SETTINGS) if settings == "both" else [settings]
        if workload["settings"] != want:
            raise ManifestError(f"{criterion} runs the settings {want}")
        if workload["cells"] != cells:
            raise ManifestError(f"{criterion} runs the cells {cells!r}")
        if (workload["mutant"] is not None) != (criterion == "C3"):
            raise ManifestError("only C3 names a mutant (or 'none' for its reference run)")
        span = workload["session_range"]
        if span is not None and (
            not isinstance(span, list) or len(span) != 2 or not 0 <= span[0] < span[1]
        ):
            raise ManifestError("workload.session_range must be null or [start, end)")
    attempt = _int(workload["attempt"], "workload.attempt", 1, 3)
    if attempt != 1 and workload.get("criterion") in ("C1", "C2", "C3"):
        # Section 11: a failed validity control is not repaired within v1.
        raise ManifestError("validity controls C1-C3 have no repair attempts")
    if attempt != 1 and workload.get("criterion") == "A7":
        # Decision D30: A7 bounds the upstream observation service, which no executor repair
        # changes; its attempt-1 result stands for every later attempt (section 11).
        raise ManifestError("A7 has no repair attempts")
    if manifest["runner"]["cpus"] != runner_cpus(manifest["vm"]["concurrency"]):
        raise ManifestError(
            f"runner.cpus must be {runner_cpus(manifest['vm']['concurrency'])} at concurrency "
            f"{manifest['vm']['concurrency']} (section 9)"
        )
    _int(workload["session_trials"], "workload.session_trials", 1, 60)
    _match(workload["cells_sha256"], SHA_RE, "workload.cells_sha256")
    boot_timeout = _int(workload["boot_timeout_s"], "workload.boot_timeout_s", 60, 900)
    settle_timeout = _int(workload["settle_timeout_s"], "workload.settle_timeout_s", 0, 300)
    sessions = _int(workload["sessions"], "workload.sessions", 1, 2000)
    trials = _int(workload["trials"], "workload.trials", 1, 100000)
    max_trial = _int(workload["max_trial_s"], "workload.max_trial_s", 5, 600)
    concurrency = manifest["vm"]["concurrency"]
    budget = (
        600 + (sessions * (boot_timeout + settle_timeout + 240) + trials * max_trial) / concurrency
    )
    if manifest["slurm"]["minutes"] * 60 < budget:
        raise ManifestError("slurm.minutes cannot cover the worst-case session budget")
    return needed


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
        optional: set[str] = {
            "mutant",
            "kill_guest_server_after_seq",
            "kill_guest_server_during_seq",
        }
        if kind == "canary-development":
            extra = {"apps", "entries", "reps", "session_trials", "measure_targets"}
            optional = set()
        _require_keys(workload, "workload", common | extra, optional)
        mutant = workload.get("mutant")
        if mutant is not None and (not isinstance(mutant, str) or not MUTANT_RE.fullmatch(mutant)):
            raise ManifestError("workload.mutant must be an operator id such as M02-...")
        for hook in ("kill_guest_server_after_seq", "kill_guest_server_during_seq"):
            # Development only: SIGKILL the guest server after this trial, or inside it before
            # its post guard, as the crash of run 622 ended it, to check that the probe and
            # the tap survive in their scopes (decision D30; never in acceptance).
            if hook in workload:
                _int(workload[hook], f"workload.{hook}", 0, 20000)
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
    if concurrency != 1 and kind != "suite-development":
        # Suite development may run N VMs at once (seed 42 only) to exercise the
        # concurrent path the ladder and A4 use; the rest run one VM at a time.
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
