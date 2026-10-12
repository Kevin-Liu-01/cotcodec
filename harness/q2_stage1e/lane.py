"""E's VM lane: S1a's lane with E's manifest rules, job order and session gaps.

Run by ``infra/slurm/host-single-node/q2e-vm.sbatch`` (S1a's ``s1a-vm.sbatch`` with this
module in place of S1a's lane) as a bare host process. Everything that runs an episode is
S1a's ``harness.q2_stage1.lane`` unchanged: the VM container from the read-only qcow2 with
the action-path v2 settings, the GPU-less episode container in the VM's ``--network none``
namespace (D12, D13), continuous dispatch, one re-queue, the stop on USR1 or the bridge's
``usr1.json``, host snapshots, the GPU job's end, the receipt and ``check_slurm``'s CPUs and
limits (S1a sections 5.5, 7.2, 14). What this module adds:

* ``validate_manifest``: E's purposes. ``development`` (pre-freeze only, the fake engine,
  dev-split tasks, no GPU) and ``e`` (post-freeze only, from a source tree whose registration
  still has its ledger row's SHA-256). An ``e`` manifest must name E's plan file (whose
  digest the registration states), run V = 20 at its size's cap, pin S1a's prompt date and
  the registered episode image, leave re-queue and the episode timeout to the lane, and hold
  exactly the plan's slots (``plan.slots``);
* **job order and DR0** (S1a sections 5.5, 11): an ``e`` manifest names the lane record file
  and receipt of every earlier E job in ``plan.job_order`` by SHA-256; the lane refuses a
  missing or changed file, and a job that fired DR0 (``records.job_dr0``);
* **session gaps**: a job of session E2-E4 starts at least 12 hours and 5 minutes after the
  later job of the session before it ended (the lane's ``t_end`` and the GPU job's recorded
  EndTime, or its Slurm start plus its time limit when Slurm reported no final state; the
  5 minutes cover the VM batch job's own end, D57 (ii)); ``submit`` passes Slurm ``--begin``
  at that time and the lane refuses to start earlier;
* **the registered engine**: before dispatching, the GPU job's argv must be S1a's
  ``plan.engine_argv`` for the job's size and its Slurm limit the job's cap;
* **the episode entry point**: ``harness.q2_stage1e.driver`` (S1a's driver with E's record
  labels) in place of ``harness.q2_stage1.driver``; the container argv is otherwise S1a's.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import signal
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from harness.q2_stage1 import lane as L1
from harness.q2_stage1 import plan as P1
from harness.q2_stage1e import plan as PE
from harness.q2_stage1e import records as RE

SCHEMA = "q2-stage1e-lane-v1"
EXPERIMENT_ID = PE.EXPERIMENT_ID
REGISTRATION = "program/preregistrations/q2-stage1-successor-e-v1.md"
LEDGER = L1.LEDGER
SPLITS = L1.SPLITS
PURPOSES = ("development", "e")
PRE_FREEZE_PURPOSES = ("development",)
BATCH = "infra/slurm/host-single-node/q2e-vm.sbatch"
DRIVER_MODULE = "harness.q2_stage1e.driver"
S1A_DRIVER_MODULE = "harness.q2_stage1.driver"
SLOT_FIELDS = (*L1.SLOT_FIELDS, "extension_block")
# The registration names the plan file it fixes on one line of this form (section 5).
PLAN_LINE = "E plan SHA-256: `{sha}`"
LaneError = L1.LaneError
_require = L1._require
sha256_file = L1.sha256_file
canonical = L1.canonical


# --------------------------------------------------------------------------- freeze state


def frozen(source_dir: Path) -> bool:
    ledger = Path(source_dir) / LEDGER
    if not ledger.is_file():
        return False
    return any(
        json.loads(line).get("experiment_id") == EXPERIMENT_ID
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def frozen_registration(source_dir: Path) -> dict[str, Any]:
    """E's ledger row, once the source tree's registration is the frozen file: the checks of
    ``scripts/preregister.py verify`` and ``check-chain`` (S1a's ``frozen_registration`` for
    E's id and file). Raises ``LaneError``."""
    ledger = Path(source_dir) / LEDGER
    _require(ledger.is_file(), f"no ledger in the source tree: {EXPERIMENT_ID} is not frozen")
    previous, row = "0" * 64, None
    for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        entry = json.loads(line)
        body = {k: v for k, v in entry.items() if k != "hash"}
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        _require(entry.get("previous_hash") == previous and entry.get("hash") == digest,
                 f"ledger line {number}: the hash chain does not hold")  # fmt: skip
        previous = digest
        if row is None and entry.get("experiment_id") == EXPERIMENT_ID:
            row = entry
    _require(row is not None, f"no ledger row for {EXPERIMENT_ID}")
    _require(row.get("path") == REGISTRATION, f"the ledger row names {row.get('path')!r}")
    path = Path(source_dir) / REGISTRATION
    _require(path.is_file() and not path.is_symlink(), f"{REGISTRATION} is missing")
    actual = sha256_file(path)
    _require(actual == row.get("sha256"),
             f"{REGISTRATION} changed after the freeze ({actual} != the ledger row's "
             f"{row.get('sha256')}); run scripts/preregister.py verify")  # fmt: skip
    return row


def dev_tasks(source_dir: Path) -> set[str]:
    return set(json.loads((Path(source_dir) / SPLITS).read_text(encoding="utf-8"))["dev"])


# --------------------------------------------------------------------------- manifests


def validate_manifest(raw: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    """E's lane manifest, checked against the registration (raises ``LaneError``)."""
    m = json.loads(json.dumps(raw))
    source_dir = Path(source_dir)
    _require(m.get("schema") == SCHEMA, f"schema must be {SCHEMA}")
    _require(m.get("experiment_id") == EXPERIMENT_ID, f"experiment_id must be {EXPERIMENT_ID}")
    purpose = m.get("purpose")
    _require(purpose in PURPOSES, f"purpose must be one of {PURPOSES}")
    _require(isinstance(m.get("name"), str) and bool(L1.SAFE.fullmatch(m["name"])), "unsafe name")
    is_frozen = frozen(source_dir)
    _require(
        purpose in PRE_FREEZE_PURPOSES or is_frozen,
        f"{purpose} runs only after the freeze (no ledger row for {EXPERIMENT_ID})",
    )
    _require(purpose not in PRE_FREEZE_PURPOSES or not is_frozen,
             f"{purpose} is a pre-freeze purpose and {EXPERIMENT_ID} is frozen: no "
             "pre-freeze job runs after the freeze")  # fmt: skip
    if purpose == "e":
        frozen_registration(source_dir)
    vm = m.get("vm") or {}
    for key, value in L1.VM_PINS.items():
        _require(vm.get(key) == value, f"vm.{key} must be {value!r} (action-path v2 2.1)")
    qcow2 = vm.get("qcow2") or {}
    _require(qcow2.get("sha256") == L1.QCOW2_SHA256, "vm.qcow2.sha256 is not the pinned guest disk")
    _require(qcow2.get("size_bytes") == L1.QCOW2_BYTES, "vm.qcow2.size_bytes differs")
    _require(str(qcow2.get("host_path", "")).startswith(L1.RUN_ROOT), "qcow2 outside the run root")
    _require(isinstance(vm.get("guest_ip"), str), "vm.guest_ip is required")
    v = vm.get("concurrency")
    _require(isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 40,
             "vm.concurrency must be 1-40")  # fmt: skip
    _require(bool(L1.IMAGE_ID.fullmatch(str(m.get("episode_image_id")))), "episode_image_id")
    osworld = m.get("osworld") or {}
    _require(osworld.get("commit") == L1.OSWORLD_COMMIT,
             f"osworld.commit must be {L1.OSWORLD_COMMIT}")  # fmt: skip
    _require(
        str(osworld.get("host_dir", "")).startswith(L1.RUN_ROOT), "osworld.host_dir outside root"
    )
    _require(str((m.get("file_cache") or {}).get("host_dir", "")).startswith(L1.RUN_ROOT),
             "file_cache.host_dir outside the run root")  # fmt: skip
    _require(m.get("mode") == "episode", "E runs mode episode only")
    _require("postconfig_probe" not in m, "postconfig_probe belongs to S1a's setup check")
    _require(m.get("fill") is None, "E has no fill rule: every job's slots are the plan's")
    engine = m.get("engine") or {}
    if purpose == "development":
        _require(engine.get("kind") == "fake", "the development purpose runs the fake engine")
        _require(isinstance(engine.get("script"), dict), "engine.script is required")
        if m.get("date") is not None:
            _require(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(m["date"]))), "date: YYYY-MM-DD")
    else:
        _require(engine.get("kind") == "bridge", "an E job runs against the engine bridge")
        _require(
            m.get("episode_image_id") == L1.EPISODE_IMAGE_ID,
            f"episode_image_id must be the registered metric image {L1.EPISODE_IMAGE_ID}",
        )
        for key in L1.FIXED_KEYS:
            _require(key not in m, f"{key} is fixed for a registered job (S1a sections 7.2, 14)")
        bridge = str(engine.get("bridge_dir", ""))
        _require(
            bridge.startswith(L1.RUN_ROOT) and "{gpu_job_id}" in bridge,
            "bridge_dir names the GPU job through {gpu_job_id} under the run root",
        )
        _require(str(engine.get("gpu_job_id_file", "")).startswith(L1.RUN_ROOT),
                 "engine.gpu_job_id_file is required with {gpu_job_id}")  # fmt: skip
        cap = engine.get("gpu_cap_min")
        _require(isinstance(cap, int) and not isinstance(cap, bool), "engine.gpu_cap_min")
        _require(
            m.get("date") == P1.PROMPT_DATE,
            f"date must be the pinned prompt date {P1.PROMPT_DATE} (S1a plan.PROMPT_DATE)",
        )
    _require(m.get("step_cap", L1.STEP_CAP) == L1.STEP_CAP, "step_cap is 15")
    _require(
        m.get("settle_after_reset_s", 60) == L1.SETTLE_AFTER_RESET_S, "settle after reset 60 s"
    )
    _require(
        m.get("settle_before_eval_s", 20) == L1.SETTLE_BEFORE_EVAL_S, "settle before eval 20 s"
    )
    slots = m.get("slots") or []
    _require(bool(slots), "no slots")
    allowed = dev_tasks(source_dir) if purpose == "development" else None
    seen: set[str] = set()
    for slot in slots:
        for key in SLOT_FIELDS:
            _require(key in slot, f"slot lacks {key}")
        _require(bool(L1.SAFE.fullmatch(str(slot["slot"]))), f"unsafe slot id {slot['slot']}")
        _require(slot["slot"] not in seen, f"duplicate slot {slot['slot']}")
        seen.add(slot["slot"])
        _require(slot["session"] in PE.SESSIONS and slot["rerun"] == PE.RERUN
                 and slot["extension_block"] is None,
                 f"slot {slot['slot']}: E's labels are sessions {PE.SESSIONS}, rerun 1, no "
                 "extension block")  # fmt: skip
        _require(slot["size"] in PE.SIZES and slot["harness"] in PE.HARNESSES,
                 f"slot {slot['slot']}: unknown size or harness")  # fmt: skip
        if allowed is not None:
            _require(slot["task_id"] in allowed,
                     f"{slot['task_id']} is not a dev-split task: no E episode touches a "
                     "confirm task before the freeze")  # fmt: skip
    if purpose == "e":
        check_plan_slots(m, source_dir)
    return m


def load_plan(m: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    """The plan file the manifest names: inside the source tree, matching its digest, E's
    registered plan, and named by the registration's plan line."""
    ref = m.get("plan") or {}
    path, sha = ref.get("path"), ref.get("sha256")
    _require(isinstance(path, str) and not path.startswith("/") and ".." not in Path(path).parts,
             "plan.path must name the plan file inside the source tree")  # fmt: skip
    _require(isinstance(sha, str) and bool(L1.HEX64.fullmatch(sha)), "plan.sha256")
    try:
        data = PE.load_plan(Path(source_dir) / path)
    except (PE.PlanError, OSError, ValueError) as exc:
        raise LaneError(f"the plan file: {exc}") from exc
    _require(data["plan_sha256"] == sha, "the plan file does not match plan.sha256")
    text = (Path(source_dir) / REGISTRATION).read_text(encoding="utf-8")
    _require(PLAN_LINE.format(sha=sha) in text, "the registration does not name this plan")
    return data


def check_plan_slots(m: Mapping[str, Any], source_dir: Path) -> None:
    """An E job's V, cap and slots are the plan's, and every earlier job ran and passed DR0."""
    plan = load_plan(m, source_dir)
    e = m.get("e") or {}
    size, session = e.get("size"), e.get("session")
    try:
        job = PE.job_name(str(size), str(session))
    except PE.PlanError as exc:
        raise LaneError(str(exc)) from exc
    _require(m["vm"]["concurrency"] == plan["V"], f"an E job runs at V = {plan['V']}")
    cap = plan["caps_minutes"][f"E-{size}"]
    _require(m["engine"].get("gpu_cap_min") == cap, f"{job}'s GPU cap is {cap} minutes")
    check_prior_jobs(e, plan, job)
    try:
        expected = PE.slots(plan, str(size), str(session))
    except PE.PlanError as exc:
        raise LaneError(str(exc)) from exc
    _require(m["slots"] == expected, f"{job}: slots differ from plan.slots")


PriorJobs = dict[str, tuple[list[dict[str, Any]], dict[str, Any]]]


def check_prior_jobs(e: Mapping[str, Any], plan: Mapping[str, Any], job: str) -> PriorJobs:
    """Every earlier E job in ``plan.job_order`` is named with its lane record file and
    receipt by SHA-256, holds that job's records only, ended (its receipt has ``t_end``)
    and did not fire DR0. Returns each earlier job's (records, receipt)."""
    order = list(plan["job_order"])
    _require(order == PE.job_order(), "the plan's job order is not the registered one")
    earlier = order[: order.index(job)]
    items = e.get("prior_jobs")
    _require(isinstance(items, list), "e.prior_jobs lists the earlier E jobs (may be empty)")
    named = [item.get("job") for item in items]
    _require(
        named == earlier,
        f"e.prior_jobs must be {earlier}, the E jobs before {job} in the registered order",
    )
    out: PriorJobs = {}
    for item in items:
        loaded = []
        for key in ("records", "receipt"):
            ref = item.get(key) or {}
            path = Path(str(ref.get("path", "")))
            _require(str(path).startswith(L1.RUN_ROOT), f"{item['job']} {key} outside the run root")
            _require(path.is_file() and sha256_file(path) == ref.get("sha256"),
                     f"{path} does not match its digest")  # fmt: skip
            loaded.append(path.read_text(encoding="utf-8"))
        rows = [json.loads(x) for x in loaded[0].splitlines() if x.strip()]
        _require(bool(rows) and all(r.get("job") == item["job"] for r in rows),
                 f"{item['job']}'s record file must hold that job's records only")  # fmt: skip
        receipt = json.loads(loaded[1])
        size, session = PE.parse_job(item["job"])
        try:
            verdict = RE.job_dr0(rows, job=item["job"], size=size, session=session,
                                 tasks=plan["tasks"], receipt=receipt)  # fmt: skip
        except RE.RecordError as exc:
            raise LaneError(f"{item['job']}'s records: {exc}") from exc
        reasons = "; ".join(verdict["reasons"])
        _require(not verdict["fires"],
                 f"DR0 fired for {item['job']} ({reasons}): no further job starts")  # fmt: skip
        _require(isinstance(receipt.get("t_end"), int | float),
                 f"{item['job']}'s receipt has no t_end")  # fmt: skip
        out[item["job"]] = (rows, receipt)
    return out


def job_end(receipt: Mapping[str, Any]) -> float:
    """A job's end: the later of the lane's ``t_end`` and the GPU job's recorded EndTime.
    When Slurm reported no final state for the GPU job (the lane's wait for it ran out), its
    EndTime is unknown and the latest it could end stands in: its Slurm start plus its time
    limit (both recorded by the lane's engine check). With neither, the end is unknown."""
    gpu_end = (receipt.get("gpu_job_end") or {}).get("end_epoch")
    if not isinstance(gpu_end, int | float):
        info = receipt.get("gpu_job") or {}
        start, limit = info.get("start_epoch"), info.get("time_limit_min")
        known = isinstance(start, int | float) and isinstance(limit, int | float)
        _require(known, "the GPU job's end is unknown: no EndTime, Slurm start or time limit")
        gpu_end = float(start) + float(limit) * 60
    return max(float(receipt["t_end"]), float(gpu_end))


def earliest_start(m: Mapping[str, Any]) -> float | None:
    """A job of E2-E4 starts at least 12 hours and 5 minutes after the later job of the
    previous session ended (``plan.session_not_before``, ``job_end``), from the receipts
    ``check_prior_jobs`` verified by digest; None for development and for E1."""
    e = m.get("e") or {}
    if m.get("purpose") != "e" or e.get("session") == PE.SESSIONS[0]:
        return None
    job = PE.job_name(str(e.get("size")), str(e.get("session")))
    ends = {}
    for item in e.get("prior_jobs") or []:
        receipt = json.loads(Path(item["receipt"]["path"]).read_text(encoding="utf-8"))
        ends[item["job"]] = job_end(receipt)
    try:
        return PE.session_not_before(job, ends)
    except PE.PlanError as exc:
        raise LaneError(str(exc)) from exc


# --------------------------------------------------------------------------- the lane


def episode_argv(cfg: L1.LaneConfig, name: str, vm: str, out_dir: Path,
                 engine_dir: Path | None, cpuset: str | None) -> list[str]:  # fmt: skip
    """S1a's episode container argv with E's entry point in place of S1a's driver."""
    argv = L1.episode_argv(cfg, name, vm, out_dir, engine_dir, cpuset)
    hits = [i for i, value in enumerate(argv) if value == S1A_DRIVER_MODULE]
    if len(hits) != 1 or argv[hits[0] - 1] != "-m":
        raise LaneError("S1a's episode argv does not run its driver module once")
    argv[hits[0]] = DRIVER_MODULE
    return argv


class Lane(L1.Lane):
    """S1a's lane, with E's session gap, engine check and episode entry point."""

    def start_engine(self) -> None:
        not_before = earliest_start(self.m)
        if not_before is not None and self.clock() < not_before:
            raise LaneError(f"a job of {(self.m.get('e') or {}).get('session')} starts at least "
                            f"{PE.SESSION_GAP_H} h {PE.SESSION_GAP_MARGIN_MIN} min after the "
                            f"previous session's later job ended: not before "
                            f"{not_before:.0f}")  # fmt: skip
        super().start_engine()
        if self.m["purpose"] == "e":
            assert self.engine_dir is not None
            status = json.loads((self.engine_dir / "ready.json").read_text(encoding="utf-8"))
            self.check_registered_engine(status)

    def check_registered_engine(self, status: Mapping[str, Any]) -> None:
        """An E job dispatches only against the registered engine: the GPU job's argv is
        S1a's ``plan.engine_argv`` for the job's size and its Slurm time limit is the job's
        cap (the minutes D22 counts)."""
        size = str((self.m.get("e") or {}).get("size"))
        expected = P1.engine_argv(P1.MODEL_DIRS[size], P1.SERVED_NAME)
        if status.get("engine_argv") != expected:
            raise LaneError(f"the GPU job's engine argv is not the registered {size} argv")
        info = self.gpu_job or {}
        cap = int(self.m["engine"]["gpu_cap_min"])
        if info.get("time_limit_min") != cap:
            raise LaneError(f"the GPU job's Slurm time limit is {info.get('time_limit_min')} "
                            f"minutes, not its cap of {cap} ({info.get('error', '')})")  # fmt: skip
        if not isinstance(info.get("start_epoch"), int | float):
            raise LaneError("the GPU job's Slurm start time is unknown")

    def episode(self, slot: L1.Slot, out_dir: Path, t_vm: float, episode_name: str, vm: str,
                cpus: Mapping[str, Any], host: dict[str, Any]) -> dict[str, Any]:  # fmt: skip
        """S1a's ``Lane.episode`` with E's container argv (``episode_argv``)."""
        config = self.episode_config(slot, out_dir, t_vm)
        (out_dir / "config.json").write_text(json.dumps(config, indent=1), encoding="utf-8")
        argv = episode_argv(self.cfg, episode_name, vm, out_dir, self.engine_dir, cpus["runner"])
        timeout = float(self.m.get("episode_timeout_s", L1.EPISODE_TIMEOUT_S))
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


# --------------------------------------------------------------------------- submission


def submit(manifest_path: Path, source_dir: Path, dry_run: bool,
           host_load_cpus: int | None = None) -> dict[str, Any]:  # fmt: skip
    """Validate, check the Slurm request (S1a's ``check_slurm``) and the host inputs (S1a's
    ``check_host``), store the canonical manifest and submit ``q2e-vm.sbatch``; a job of
    E2-E4 is held by ``--begin`` until its session gap has passed."""
    m = validate_manifest(json.loads(Path(manifest_path).read_text(encoding="utf-8")), source_dir)
    request = L1.check_slurm(m, host_load_cpus)
    cpus, memory, minutes = request["cpus"], request["memory_gb"], request["minutes"]
    host = L1.check_host(m)
    text = canonical(m)
    digest = hashlib.sha256(text.encode()).hexdigest()
    run_root = Path(m["run_root"])
    _require(str(run_root).startswith(L1.RUN_ROOT), "run_root outside the run root")
    stored = run_root / "manifests" / f"{digest}.json"
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_text(text, encoding="utf-8")
    batch = Path(source_dir) / BATCH
    env = {
        "COTCODEC_S1A_MANIFEST_PATH_HEX": str(stored).encode().hex(),
        "COTCODEC_S1A_MANIFEST_SHA256": digest,
        "COTCODEC_BATCH_SHA256": sha256_file(batch),
        "COTCODEC_SOURCE_HOST_HEX": str(Path(source_dir).resolve()).encode().hex(),
        "COTCODEC_SOURCE_TREE_SHA256": L1.tree_sha256(Path(source_dir)),
        "COTCODEC_RUN_ROOT_HEX": str(run_root).encode().hex(),
    }
    hours, mins = divmod(minutes, 60)
    argv = ["sbatch", "--parsable", f"--cpus-per-task={cpus}", f"--mem={memory}G",
            f"--time={hours:02d}:{mins:02d}:00", f"--job-name=q2e-{m['name']}"[:60]]  # fmt: skip
    not_before = earliest_start(m)
    if not_before is not None:
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
    run = sub.add_parser("run", help="run a validated manifest (inside q2e-vm.sbatch)")
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
                        help="temporary host-load CPU cap (development only)")  # fmt: skip
    args = parser.parse_args(argv)
    if args.command == "submit":
        out = submit(args.manifest, args.source_dir, args.dry_run, args.host_load_max_cpus)
        print(json.dumps(out, indent=1))
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

    cpusets = L1.plan_cpusets(slurm_cpu_ids(args.job_id), manifest["vm"]["concurrency"],
                              manifest["vm"]["cpu_cores"])  # fmt: skip
    lane = Lane(
        L1.LaneConfig(manifest, args.job_id, args.run_dir, args.source_dir),
        cpusets=cpusets,
        snapshot=snapshot_host,
    )
    signal.signal(signal.SIGUSR1, lambda *_: lane.stop.set())
    receipt = lane.run()
    print(json.dumps({k: receipt[k] for k in ("records", "statuses", "stopped")}))
    return 0 if "error" not in receipt else 3


if __name__ == "__main__":
    raise SystemExit(main())
