#!/usr/bin/env python3
"""Fill the dense headroom pre-check's lane manifests from measured artifacts only.

Templates: ``experiments/manifests/q3-dense-headroom-precheck-v1/*.yaml`` (one
per lane). Their ``FILL-*`` values are the image's ID, git SHA and source-tar
SHA-256 (from its build receipt) and the frozen preregistration's SHA-256
(which must equal its ledger row). The filler refuses unless

* every file in the frozen preregistration's code table has the tabled SHA-256
  in this checkout and at the image's commit, which must hold the ledger row;
* each lane's GPU count, limit and cap equal the registered lane
  (``harness.dense_headroom_data.LANES``) and the registered caps sum to at most
  0.5 GPU-h (program decision D26);
* a continuation (``--continuation-of JOB --used-minutes N``) is the lane's
  only one: it gets the lane's minutes minus the minutes used (plus one), at
  least 3, in the same run root, resumed from ``dense-precheck/checkpoints``.

Exit codes: 0 filled, 2 an input is missing or inconsistent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
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
IDENTITY_ROW_RE = re.compile(r"^\| ([A-Za-z0-9_./-]+\.(?:py|yaml)) \| ([0-9a-f]{64}) \|$", re.M)
IMAGE_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
JOB_RE = re.compile(r"^[1-9][0-9]{0,9}$")
MIN_CONTINUATION_MINUTES = 3
RESUME_SUBPATH = "dense-precheck/checkpoints"


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


def check_image_commit(repo_root: Path, git_sha: str, row: dict[str, Any],
                       table: dict[str, str]) -> None:
    ledger = _git_show(repo_root, git_sha, "program/preregistrations/ledger.jsonl").decode()
    if str(row["hash"]) not in ledger:
        raise FillError("the image commit does not contain the frozen ledger row")
    for path, digest in table.items():
        if hashlib.sha256(_git_show(repo_root, git_sha, path)).hexdigest() != digest:
            raise FillError(f"{path} at the image commit is not the tabled code")


def continuation_minutes(lane: dhd.Lane, used_minutes: float) -> int:
    remaining = lane.minutes - (math.ceil(used_minutes) + 1)
    if remaining < MIN_CONTINUATION_MINUTES:
        raise FillError(f"{lane.lane_id}: {remaining} minutes remain; no continuation")
    return remaining


def fill(lane_id: str, image_receipt: Path, repo_root: Path, output: Path, *,
         template_dir: Path = TEMPLATE_DIR, continuation_of: str | None = None,
         used_minutes: float | None = None) -> Path:
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
    table = dict(IDENTITY_ROW_RE.findall(
        (repo_root / str(row["path"])).read_text(encoding="utf-8")))
    if SELF_PATH not in table:
        raise FillError("the frozen preregistration lacks its code digest table")
    for path, digest in table.items():
        if _sha256(PROJECT_ROOT / path) != digest:
            raise FillError(f"{path} is not the code tabled in the frozen preregistration")
    template = template_dir / TEMPLATES[lane_id]
    text = template.read_text(encoding="utf-8")
    for key, value in sorted(values.items(), key=lambda item: -len(item[0])):
        text = text.replace(f'"{key}"', f'"{value}"').replace(key, value)
    remaining = sorted(set(re.findall(r"FILL-[a-z0-9-]+", text)))
    if remaining:
        raise FillError(f"unfilled values remain: {remaining}")
    manifest = yaml.safe_load(text)
    check_resources(manifest, lane, lane.minutes)
    check_image_commit(repo_root, values["FILL-image-git-sha"], row, table)
    name = template.name
    if continuation_of is not None:
        if not JOB_RE.fullmatch(str(continuation_of)) or used_minutes is None:
            raise FillError("a continuation needs a Slurm job id and the minutes it used")
        target = output / name.replace(".yaml", "-continuation.yaml")
        if target.exists():
            raise FillError("this lane already has its one continuation")
        manifest["name"] = f"{manifest['name']}-cont"
        manifest["resources"]["minutes"] = continuation_minutes(lane, used_minutes)
        manifest["resume_from_job_id"] = str(continuation_of)
        manifest["resume_subpath"] = RESUME_SUBPATH
        text = yaml.safe_dump(manifest, sort_keys=False)
        name = target.name
    output.mkdir(parents=True, exist_ok=True)
    target = output / name
    if target.exists() and target.read_text(encoding="utf-8") != text:
        raise FillError(f"{target} exists with different content; never overwrite")
    target.write_text(text, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--lane", required=True, choices=sorted(dhd.LANES))
    parser.add_argument("--image-receipt", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--continuation-of", default=None)
    parser.add_argument("--used-minutes", type=float, default=None)
    args = parser.parse_args(argv)
    try:
        target = fill(args.lane, args.image_receipt, args.repo_root, args.output,
                      continuation_of=args.continuation_of, used_minutes=args.used_minutes)
    except (OSError, KeyError, ValueError, json.JSONDecodeError,
            preregister.PreregistrationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"filled": str(target)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
