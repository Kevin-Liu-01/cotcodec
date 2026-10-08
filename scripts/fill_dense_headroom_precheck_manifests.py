#!/usr/bin/env python3
"""Fill the dense headroom pre-check's lane manifests from measured artifacts only.

Templates: ``experiments/manifests/q3-dense-headroom-precheck-v1/*.yaml`` (one
per lane, each tabled with its SHA-256 in the frozen preregistration). Their
``FILL-*`` values are the image's ID, git SHA and source-tar SHA-256 (from its
build receipt) and the frozen preregistration's SHA-256 (which must equal its
ledger row). The filler refuses unless

* every file in the frozen preregistration's code table (the lane templates
  and ``scripts/preregister.py`` among them) has the tabled SHA-256 in this
  checkout and at the image's commit, which must hold the ledger row;
* the filled manifest is the template with only its ``FILL-*`` values
  replaced (argv element by element, every other field unchanged), and its GPU
  count, limit, cap, profile, lane, model and seeds are the registered lane's
  (``harness.dense_headroom_data.LANES``); the registered caps sum to at most
  0.5 GPU-h (program decision D26);
* every job of the lane counts against the lane's own minutes. The lane's run
  root (the template's ``run_root``) is read: every job directory in it must
  have ended (``job.env`` and ``termination.env`` naming its job id), none may
  hold a lane receipt, and each is charged its elapsed minutes
  (``started_at`` to ``finished_at``) rounded up, plus one for the Slurm
  prolog before ``job.env`` and the epilogue after ``termination.env``. The
  first job gets the lane's minutes; a later job gets the minutes left, at
  least 5 (``MIN_JOB_MINUTES``: the 3-minute SIGUSR1 lead plus 2 useful
  minutes), or is refused;
* a later job is a continuation (``--continuation-of JOB``) or a re-run of a
  void job. A continuation resumes ``dense-precheck/checkpoints`` of JOB, which
  must be the lane's latest job and have ended with a confirmed signal
  checkpoint (exit code 75); its limit is at most the lane's minutes minus two,
  and the lane has at most one continuation ever (no job in the run root names
  a predecessor and no slot was claimed for one);
* every job, the first included, claims its slot before its manifest is
  written: ``<run_root>/fill-claims/after-<N>.json``, created exclusively,
  where N is the number of the lane's ended jobs (0 for the first job). Filling
  the same slot again is refused unless the manifest is byte-identical, so no
  ``--output`` choice can fill two jobs (or two continuations) for one slot.
  Each filled manifest is submitted once. A job is matched to its claim by its
  ``manifest.json`` (name, minutes, image and predecessor); a lane with a job
  that has no claim, a job that ran longer than its claim's minutes, or two
  jobs on one claim (a filled manifest submitted again) is void, and the filler
  fills no further job of it (``claim_problems``; the summariser voids the
  lane on the same rule). The entry point cannot check claims: only its own job
  directory is mounted in the container, not the lane's run root;
* the Qwen3.5-4B-Base lane is filled only with ``--small-lane-receipt``, the
  Qwen3-0.6B-Base lane's completed receipt of this registration whose
  ``smoke_452_reproduction`` status is REPRODUCED (decisions 1 and 11).

Because Slurm sends SIGUSR1 three minutes before the limit and the job ends
there wherever the signal lands, a job's useful time is its limit minus three
minutes, and a job interrupted at its time limit leaves at most two minutes
of the lane: a continuation fits only after an earlier interruption (a
SIGTERM from the operator or the node, or a SIGUSR1 sent by hand).

Exit codes: 0 filled, 2 an input is missing or inconsistent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import dense_headroom_data as dhd  # noqa: E402
from scripts import preregister  # noqa: E402

TEMPLATE_DIR = PROJECT_ROOT / "experiments" / "manifests" / "q3-dense-headroom-precheck-v1"
TEMPLATES = {"qwen3-0.6b-base": "q3-dense-headroom-0p6b.yaml",
             "qwen3.5-4b-base": "q3-dense-headroom-4b.yaml"}
SELF_PATH = "scripts/fill_dense_headroom_precheck_manifests.py"
BOUND_PATHS = (SELF_PATH, "scripts/preregister.py",
               *(f"experiments/manifests/q3-dense-headroom-precheck-v1/{name}"
                 for name in TEMPLATES.values()))
IDENTITY_ROW_RE = re.compile(r"^\| ([A-Za-z0-9_./-]+\.(?:py|yaml)) \| ([0-9a-f]{64}) \|$", re.M)
IMAGE_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
JOB_RE = re.compile(r"^[1-9][0-9]{0,19}$")
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CHECKPOINT_REASONS = ("signal_USR1_checkpoint_confirmed", "signal_TERM_checkpoint_confirmed")
CLAIMS_DIR = "fill-claims"
RECEIPT = Path(dhd.OUTPUT_SUBDIR) / "receipt.json"


class FillError(ValueError):
    """An input needed to fill a manifest is missing or inconsistent."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_show(repo_root: Path, revision: str, path: str) -> bytes:
    completed = subprocess.run(["git", "-C", str(repo_root), "show", f"{revision}:{path}"],
                               capture_output=True, check=False)
    if completed.returncode != 0:
        raise FillError(f"{path} is not present at image commit {revision}")
    return completed.stdout


def env_file(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator:
                fields[key] = value
    return fields


def check_budget() -> None:
    total = dhd.registered_caps_total()
    if total > dhd.TOTAL_CAP_GPU_HOURS + 1e-9:
        raise FillError(f"registered caps {total} GPU-h exceed {dhd.TOTAL_CAP_GPU_HOURS} (D26)")
    for lane in dhd.LANES.values():
        if lane.gpus * lane.minutes / 60 > lane.cap_gpu_hours + 1e-9:
            raise FillError(f"{lane.lane_id}: {lane.gpus} x {lane.minutes} min exceeds its cap")


def check_resources(manifest: dict[str, Any], lane: dhd.Lane, minutes: int) -> None:
    """Refuse a manifest whose GPUs, limit, cap, profile or lane differ from the registration."""

    resources = manifest.get("resources") or {}
    budget = manifest.get("budget") or {}
    if resources.get("gpus") != lane.gpus:
        raise FillError(f"{lane.lane_id}: the manifest must request {lane.gpus} GPU")
    if resources.get("minutes") != minutes:
        raise FillError(f"{lane.lane_id}: the manifest limit must be {minutes} minutes")
    if budget.get("max_gpu_hours") != lane.cap_gpu_hours:
        raise FillError(f"{lane.lane_id}: the manifest cap must be {lane.cap_gpu_hours} GPU-h")
    if manifest.get("container_profile") != lane.container_profile:
        raise FillError(f"{lane.lane_id}: container_profile must be {lane.container_profile}")
    command = manifest.get("command") or []
    if "--lane" not in command or command[command.index("--lane") + 1] != lane.lane_id:
        raise FillError(f"{lane.lane_id}: the command runs another lane")
    model = manifest.get("model") or {}
    if (model.get("model_id"), model.get("revision"), model.get("receipt_sha256"),
            model.get("artifact_root_sha256")) != (lane.model_id, lane.revision,
                                                   lane.receipt_sha256,
                                                   lane.artifact_root_sha256):
        raise FillError(f"{lane.lane_id}: the model block is not the registered receipt")
    if manifest.get("seeds") != list(dhd.SEEDS):
        raise FillError(f"{lane.lane_id}: seeds must be {list(dhd.SEEDS)}")


def _substitute(value: Any, values: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: _substitute(v, values) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, values) for v in value]
    if isinstance(value, str) and value in values:
        return values[value]
    return value


def check_against_template(manifest: dict[str, Any], template: dict[str, Any],
                           values: dict[str, str]) -> None:
    """The filled manifest is the template with only its FILL-* scalars replaced."""

    expected = _substitute(template, values)
    if manifest.get("command") != expected.get("command"):
        raise FillError("the filled argv is not the template's argv")
    if manifest != expected:
        differing = sorted(k for k in set(manifest) | set(expected)
                           if manifest.get(k) != expected.get(k))
        raise FillError(f"the filled manifest differs from the template in {differing}")


def check_image_commit(repo_root: Path, git_sha: str, row: dict[str, Any],
                       table: dict[str, str]) -> None:
    ledger = _git_show(repo_root, git_sha, "program/preregistrations/ledger.jsonl").decode()
    if str(row["hash"]) not in ledger:
        raise FillError("the image commit does not contain the frozen ledger row")
    for path, digest in table.items():
        if hashlib.sha256(_git_show(repo_root, git_sha, path)).hexdigest() != digest:
            raise FillError(f"{path} at the image commit is not the tabled code")


# --------------------------------------------------------------------------- #
# The lane's jobs in its run root
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LaneJob:
    """One ended Slurm job directory in a lane's run root."""

    job_id: str
    path: Path
    reason: str
    exit_code: str
    checkpoint_ready: bool
    predecessor_job_id: str | None
    elapsed_seconds: float
    has_receipt: bool
    # From the job's manifest.json (the submitter's manifest, written by the
    # batch script before job.env): what the job was submitted as, matched
    # against the fill claims. None when the file is missing or unreadable.
    manifest_key: tuple[Any, ...] | None = None

    @property
    def charged_minutes(self) -> int:
        return math.ceil(self.elapsed_seconds / 60.0) + 1

    @property
    def checkpointed(self) -> bool:
        return (self.reason in CHECKPOINT_REASONS and self.exit_code == "75"
                and self.checkpoint_ready
                and (self.path / dhd.RESUME_SUBPATH / "dev-artifact.sha256").is_file())

    def as_dict(self) -> dict[str, Any]:
        return {"job_id": self.job_id, "reason": self.reason, "exit_code": self.exit_code,
                "checkpoint_ready": self.checkpoint_ready,
                "predecessor_job_id": self.predecessor_job_id,
                "elapsed_seconds": self.elapsed_seconds,
                "charged_minutes": self.charged_minutes, "has_receipt": self.has_receipt,
                "manifest": (dict(zip(MANIFEST_KEY_FIELDS, self.manifest_key, strict=True))
                             if self.manifest_key is not None else None)}


# The manifest fields that identify a filled job: its name (the template's for
# the first job, ``-rerun-<N>`` or ``-cont`` for a later one), its limit, its
# image and its predecessor.
MANIFEST_KEY_FIELDS = ("name", "minutes", "image_id", "predecessor_job_id")


def manifest_key(name: Any, minutes: Any, image_id: Any, predecessor: Any) -> tuple[Any, ...]:
    return (name, minutes, image_id, None if predecessor in (None, "", "none")
            else str(predecessor))


def job_manifest_key(path: Path) -> tuple[Any, ...] | None:
    """The key of the manifest a job directory was submitted with, or None."""

    try:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(manifest, dict):
        return None
    return manifest_key(manifest.get("name"), manifest.get("minutes"),
                        manifest.get("image_id"), manifest.get("resume_from_job_id"))


def lane_jobs(run_root: Path) -> list[LaneJob]:
    """Every job directory in the lane's run root, oldest first; each must have ended."""

    jobs: list[LaneJob] = []
    if not run_root.is_dir():
        return jobs
    for path in run_root.iterdir():
        if not JOB_RE.fullmatch(path.name):
            continue
        if path.is_symlink() or not path.is_dir():
            raise FillError(f"{path.name} in the lane's run root is not a job directory")
        job = env_file(path / "job.env")
        end = env_file(path / "termination.env")
        if job.get("job_id") != path.name or end.get("job_id") != path.name:
            raise FillError(f"job {path.name} has not ended (or ended before the batch script "
                            "recorded it): it cannot be charged, so no further job of this "
                            "lane is filled")
        try:
            elapsed = (datetime.strptime(end["finished_at"], TIME_FORMAT)
                       - datetime.strptime(job["started_at"], TIME_FORMAT)).total_seconds()
        except (KeyError, ValueError) as exc:
            raise FillError(f"job {path.name}: unreadable start or finish time") from exc
        if elapsed < 0:
            raise FillError(f"job {path.name} finished before it started")
        predecessor = job.get("predecessor_job_id", "none")
        jobs.append(LaneJob(
            job_id=path.name, path=path, reason=end.get("reason", ""),
            exit_code=end.get("exit_code", ""),
            checkpoint_ready=end.get("checkpoint_ready") == "true",
            predecessor_job_id=None if predecessor in ("", "none") else predecessor,
            elapsed_seconds=elapsed, has_receipt=(path / RECEIPT).exists(),
            manifest_key=job_manifest_key(path)))
    return sorted(jobs, key=lambda j: int(j.job_id))


def lane_charge(jobs: list[LaneJob]) -> int:
    return sum(job.charged_minutes for job in jobs)


def read_claims(run_root: Path) -> list[dict[str, Any]]:
    claims = run_root / CLAIMS_DIR
    if not claims.is_dir():
        return []
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(claims.glob("after-*.json"))]


def claim_problems(jobs: list[LaneJob], claims: list[dict[str, Any]]) -> list[str]:
    """Why the lane's jobs void it under the claim rule (decision 12 as amended
    in D32), or nothing. Every job must match one fill claim by its manifest
    (name, minutes, image, predecessor), no job may run longer than its claim's
    minutes, and no claim may carry two jobs (a filled manifest submitted
    again)."""

    by_key: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for claim in claims:
        key = manifest_key(claim.get("manifest_name"), claim.get("minutes"),
                           claim.get("image_id"), claim.get("predecessor_job_id"))
        by_key.setdefault(key, []).append(claim)
    problems: list[str] = []
    holders: dict[tuple[Any, ...], list[str]] = {}
    for job in jobs:
        matches = by_key.get(job.manifest_key, []) if job.manifest_key is not None else []
        if len(matches) != 1:
            problems.append(f"job {job.job_id} has no fill claim" if not matches else
                            f"job {job.job_id} matches {len(matches)} fill claims")
            continue
        holders.setdefault(job.manifest_key, []).append(job.job_id)
        minutes = matches[0].get("minutes")
        if (not isinstance(minutes, int) or isinstance(minutes, bool)
                or job.elapsed_seconds > minutes * 60):
            problems.append(f"job {job.job_id} ran {job.elapsed_seconds:.0f} s, more than its "
                            f"claim's {minutes} minutes")
    for key, job_ids in holders.items():
        if len(job_ids) > 1:
            problems.append(f"jobs {job_ids} ran on one fill claim (slot "
                            f"{by_key[key][0].get('slot')}): a filled manifest was submitted "
                            "more than once")
    return problems


@dataclass(frozen=True)
class NextJob:
    kind: str  # first | re-run | continuation
    minutes: int
    slot: int  # ended jobs of the lane before this one
    predecessor_job_id: str | None
    charged_minutes: int


def plan_next_job(lane: dhd.Lane, run_root: Path, continuation_of: str | None) -> NextJob:
    """What the lane's next job may be, from its run root alone."""

    jobs = lane_jobs(run_root)
    if any(job.has_receipt for job in jobs):
        raise FillError(f"{lane.lane_id} already has a lane receipt; no further job runs under "
                        "this id")
    problems = claim_problems(jobs, read_claims(run_root))
    if problems:
        raise FillError(f"{lane.lane_id} is void ({'; '.join(problems)}); no further job of it "
                        "is filled, and the lane is INCOMPLETE")
    charged = lane_charge(jobs)
    remaining = lane.minutes - charged
    # A continuation claimed for an earlier slot counts as the lane's one
    # continuation (it ran, or other jobs ran instead); the current slot's claim
    # is checked by claim_slot, so refilling the identical manifest is allowed.
    claimed_continuation = any(
        claim.get("kind") == "continuation" and claim.get("slot") != len(jobs)
        for claim in read_claims(run_root))
    if continuation_of is None:
        if not jobs:
            return NextJob("first", lane.minutes, 0, None, 0)
        if remaining < dhd.MIN_JOB_MINUTES:
            raise FillError(f"{lane.lane_id}: {remaining} of {lane.minutes} minutes remain after "
                            f"{len(jobs)} job(s); the lane is INCOMPLETE")
        return NextJob("re-run", remaining, len(jobs), None, charged)
    if not JOB_RE.fullmatch(str(continuation_of)):
        raise FillError("--continuation-of needs a Slurm job id")
    if not jobs or jobs[-1].job_id != str(continuation_of):
        raise FillError(f"job {continuation_of} is not the lane's latest job")
    if claimed_continuation or any(job.predecessor_job_id for job in jobs):
        raise FillError(f"{lane.lane_id} already has its one continuation")
    if not jobs[-1].checkpointed:
        raise FillError(f"job {continuation_of} did not end with a confirmed signal checkpoint "
                        "and its development checkpoint")
    top = lane.minutes - dhd.CONTINUATION_MIN_CHARGE
    minutes = min(remaining, top)
    if minutes < dhd.MIN_JOB_MINUTES:
        raise FillError(f"{lane.lane_id}: {remaining} of {lane.minutes} minutes remain; no "
                        "continuation within the lane's cap; the lane is INCOMPLETE")
    return NextJob("continuation", minutes, len(jobs), str(continuation_of), charged)


def later_job_manifest(manifest: dict[str, Any], plan: NextJob) -> dict[str, Any]:
    """The template's manifest for a re-run or a continuation."""

    out = json.loads(json.dumps(manifest))
    out["resources"]["minutes"] = plan.minutes
    if plan.kind == "continuation":
        out["name"] = f"{manifest['name']}-cont"
        out["resume_from_job_id"] = plan.predecessor_job_id
        out["resume_subpath"] = dhd.RESUME_SUBPATH
    elif plan.kind == "re-run":
        out["name"] = f"{manifest['name']}-rerun-{plan.slot}"
    else:
        raise FillError("the first job uses the template unchanged")
    return out


def claim_slot(run_root: Path, lane: dhd.Lane, plan: NextJob, text: str,
               image_id: str) -> Path:
    """Claim the lane's slot ``plan.slot`` for this job (the first included), once."""

    manifest = yaml.safe_load(text)
    if (not isinstance(manifest, dict)
            or manifest_key(manifest.get("name"), (manifest.get("resources") or {}).get("minutes"),
                            manifest.get("image_id"), manifest.get("resume_from_job_id"))
            != manifest_key(manifest.get("name"), plan.minutes, image_id,
                            plan.predecessor_job_id)):
        raise FillError("the manifest is not the planned job's")
    claims = run_root / CLAIMS_DIR
    claims.mkdir(parents=True, exist_ok=True)
    path = claims / f"after-{plan.slot}.json"
    payload = json.dumps({"lane": lane.lane_id, "slot": plan.slot, "kind": plan.kind,
                          "minutes": plan.minutes,
                          "predecessor_job_id": plan.predecessor_job_id,
                          "charged_minutes": plan.charged_minutes, "image_id": image_id,
                          "manifest_name": manifest["name"],
                          "manifest_sha256": hashlib.sha256(text.encode()).hexdigest()},
                         indent=2, sort_keys=True) + "\n"
    try:
        handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != payload:
            raise FillError(f"slot {plan.slot} of {lane.lane_id} is already claimed by another "
                            f"job ({path}); submit that one") from None
        return path
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(payload)
    return path


# --------------------------------------------------------------------------- #
# The 4B lane waits on the 0.6B lane's smoke reproduction
# --------------------------------------------------------------------------- #


GATED_LANE, GATING_LANE = "qwen3.5-4b-base", "qwen3-0.6b-base"


def check_small_lane_receipt(path: Path | None, preregistration_sha256: str) -> dict[str, Any]:
    """The 4B lane is filled only after the 0.6B lane's completed receipt of this
    registration reports the K1 smoke reproduction REPRODUCED (decisions 1 and
    11, Freeze procedure step 4). It never depends on the 0.6B headroom read."""

    if path is None:
        raise FillError(f"{GATED_LANE} is filled only with --small-lane-receipt, the "
                        f"{GATING_LANE} lane's receipt whose smoke_452_reproduction is "
                        "REPRODUCED")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FillError(f"the {GATING_LANE} receipt is unreadable: {exc}") from exc
    if not isinstance(receipt, dict):
        raise FillError(f"the {GATING_LANE} receipt is not a JSON object")
    hashes = receipt.get("hashes") or {}
    lane = (receipt.get("lane") or {}).get("lane_id")
    if (receipt.get("experiment_id"), lane, receipt.get("profile"),
            receipt.get("status")) != (dhd.EXPERIMENT_ID, GATING_LANE, "registered",
                                       "PRECHECK_COMPLETE"):
        raise FillError(f"{path} is not a completed {GATING_LANE} receipt of "
                        f"{dhd.EXPERIMENT_ID}")
    if hashes.get("preregistration_sha256") != preregistration_sha256:
        raise FillError(f"{path} was read against another preregistration")
    reproduction = (receipt.get("report") or {}).get("smoke_452_reproduction") or {}
    if reproduction.get("status") != "REPRODUCED":
        raise FillError(f"the {GATING_LANE} lane's K1 smoke reproduction is "
                        f"{reproduction.get('status')}: the combined read is INVALID and "
                        f"{GATED_LANE} is not run")
    return {"slurm_job_id": receipt.get("slurm_job_id"), "status": "REPRODUCED"}


# --------------------------------------------------------------------------- #
# Filling
# --------------------------------------------------------------------------- #


def fill(lane_id: str, image_receipt: Path, repo_root: Path, output: Path, *,
         template_dir: Path = TEMPLATE_DIR, continuation_of: str | None = None,
         run_root: Path | None = None, small_lane_receipt: Path | None = None) -> Path:
    if lane_id not in dhd.LANES:
        raise FillError(f"unknown registered lane {lane_id!r}")
    lane = dhd.LANES[lane_id]
    check_budget()
    receipt = json.loads(image_receipt.read_text(encoding="utf-8"))
    values = {"FILL-image-id": receipt["image_id"], "FILL-image-git-sha": receipt["git_sha"],
              "FILL-image-source-tar-sha256": receipt["source_tar_sha256"]}
    if not IMAGE_RE.fullmatch(values["FILL-image-id"]):
        raise FillError("image receipt image_id is not a local sha256 image id")
    if not GIT_RE.fullmatch(values["FILL-image-git-sha"]):
        raise FillError("image receipt git_sha is not 40 hex")
    if not SHA_RE.fullmatch(values["FILL-image-source-tar-sha256"]):
        raise FillError("image receipt source_tar_sha256 is not 64 hex")
    row = preregister.verify(dhd.EXPERIMENT_ID,
                             ledger=repo_root / "program" / "preregistrations" / "ledger.jsonl",
                             root=repo_root)
    values["FILL-preregistration-sha256"] = str(row["sha256"])
    if lane_id == GATED_LANE:
        check_small_lane_receipt(small_lane_receipt, str(row["sha256"]))
    table = dict(IDENTITY_ROW_RE.findall(
        (repo_root / str(row["path"])).read_text(encoding="utf-8")))
    missing = [path for path in BOUND_PATHS if path not in table]
    if missing:
        raise FillError(f"the frozen preregistration does not table {missing}")
    for path, digest in table.items():
        if _sha256(PROJECT_ROOT / path) != digest:
            raise FillError(f"{path} is not the code tabled in the frozen preregistration")
    template = template_dir / TEMPLATES[lane_id]
    relative = f"experiments/manifests/q3-dense-headroom-precheck-v1/{template.name}"
    if _sha256(template) != table[relative]:
        raise FillError(f"{template} is not the tabled template")
    raw = template.read_text(encoding="utf-8")
    text = raw
    for key, value in sorted(values.items(), key=lambda item: -len(item[0])):
        text = text.replace(f'"{key}"', f'"{value}"').replace(key, value)
    remaining = sorted(set(re.findall(r"FILL-[a-z0-9-]+", text)))
    if remaining:
        raise FillError(f"unfilled values remain: {remaining}")
    manifest = yaml.safe_load(text)
    check_against_template(manifest, yaml.safe_load(raw), values)
    check_resources(manifest, lane, lane.minutes)
    check_image_commit(repo_root, values["FILL-image-git-sha"], row, table)
    run_root = run_root or Path(manifest["run_root"])
    plan = plan_next_job(lane, run_root, continuation_of)
    name = template.name
    if plan.kind != "first":
        manifest = later_job_manifest(manifest, plan)
        text = yaml.safe_dump(manifest, sort_keys=False)
        name = name.replace(".yaml", f"-{plan.kind}-after-{plan.slot}.yaml")
    output.mkdir(parents=True, exist_ok=True)
    target = output / name
    if target.exists() and target.read_text(encoding="utf-8") != text:
        raise FillError(f"{target} exists with different content; never overwrite")
    claim_slot(run_root, lane, plan, text, values["FILL-image-id"])  # every job, slot 0 too
    target.write_text(text, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--lane", required=True, choices=sorted(dhd.LANES))
    parser.add_argument("--image-receipt", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--continuation-of", default=None)
    parser.add_argument("--run-root", type=Path, default=None,
                        help="the lane's run root (default: the template's run_root)")
    parser.add_argument("--small-lane-receipt", type=Path, default=None,
                        help=f"for {GATED_LANE}: the {GATING_LANE} lane's receipt.json, whose "
                             "smoke_452_reproduction must be REPRODUCED")
    args = parser.parse_args(argv)
    try:
        target = fill(args.lane, args.image_receipt, args.repo_root, args.output,
                      continuation_of=args.continuation_of, run_root=args.run_root,
                      small_lane_receipt=args.small_lane_receipt)
    except (OSError, KeyError, ValueError, json.JSONDecodeError,
            preregister.PreregistrationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"filled": str(target)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
