#!/usr/bin/env python3
"""Fill q3-dense-headroom-precheck-v2's manifests from measured artifacts only.

Templates: ``experiments/manifests/q3-dense-headroom-precheck-v2/*.yaml``: the
two lanes (tabled in the frozen preregistration) and the two development
timing jobs (D36 and D42 (ii); filled before the freeze). Their ``FILL-*`` values are the image's
ID, git SHA and source-tar SHA-256 (from its build receipt) and, for a lane,
the frozen preregistration's SHA-256 (which must equal its ledger row).

The lane rules are v1's, applied by v1's own functions
(``scripts/fill_dense_headroom_precheck_manifests.py``, imported unchanged):
the filled manifest is the template with only its ``FILL-*`` values replaced;
every tabled file has its tabled digest here and at the image's commit, which
holds the ledger row; every job of a lane is charged against the lane's own
minutes from its run root; every job, the first included, claims its slot
exclusively; a continuation follows a confirmed signal checkpoint, at most
once per lane. The lanes' minutes and caps are v2's
(``harness/dense_headroom_v2_lanes.py``), and the caps plus the timing job's
sum to at most 1.5 GPU-h (D36; both timing jobs included, D42).

The Qwen3.5-4B-Base lane is filled only with ``--small-lane-receipt``: the
Qwen3-0.6B-Base lane's completed receipt of this registration, bound to its
Slurm job, whose K1 smoke-452 reproduction is REPRODUCED and which reproduces
v1's job-727 receipt statistics (the registered validity gate).

``--timing [N]`` fills development timing job N instead (1, the default: D36's,
Slurm 766; 2: D42's, which times the fixed 4B path): before the freeze, no
preregistration, that job's template with its three image values, one claim
(slot 0 of that job's own run root) so that it is submitted once and
accounted apart from the other.

Exit codes: 0 filled, 2 an input is missing or inconsistent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import dense_headroom_data as dhd  # noqa: E402
from harness import dense_headroom_v2 as dv2  # noqa: E402
from harness import dense_headroom_v2_lanes as lanes  # noqa: E402
from scripts import fill_dense_headroom_precheck_manifests as v1f  # noqa: E402
from scripts import preregister  # noqa: E402

FillError = v1f.FillError
TEMPLATE_DIR = PROJECT_ROOT / "experiments" / "manifests" / "q3-dense-headroom-precheck-v2"
TEMPLATE_PREFIX = "experiments/manifests/q3-dense-headroom-precheck-v2"
TEMPLATES = {"qwen3-0.6b-base": "q3-dense-headroom-v2-0p6b.yaml",
             "qwen3.5-4b-base": "q3-dense-headroom-v2-4b.yaml"}
TIMING_TEMPLATE = "q3-dense-headroom-v2-timing-4b.yaml"  # D36's timing job (Slurm 766)
# Development timing job number -> template; each template has its own run root (D42 (ii)).
TIMING_TEMPLATES = {1: TIMING_TEMPLATE, 2: "q3-dense-headroom-v2-timing-2-4b.yaml"}
SELF_PATH = "scripts/fill_dense_headroom_precheck_v2_manifests.py"
BOUND_PATHS = (SELF_PATH, "scripts/fill_dense_headroom_precheck_manifests.py",
               "scripts/preregister.py",
               *(f"{TEMPLATE_PREFIX}/{name}"
                 for name in (*TEMPLATES.values(), *TIMING_TEMPLATES.values())))
GATED_LANE, GATING_LANE = "qwen3.5-4b-base", "qwen3-0.6b-base"
TIMING_VALUES = ("FILL-image-id", "FILL-image-git-sha", "FILL-image-source-tar-sha256")


def check_budget() -> None:
    total = lanes.registered_caps_total()
    if total > lanes.TOTAL_CAP_GPU_HOURS + 1e-9:
        raise FillError(f"registered caps {total} GPU-h exceed {lanes.TOTAL_CAP_GPU_HOURS} (D36)")
    for lane in lanes.LANES.values():
        if lane.gpus * lane.minutes / 60 > lane.cap_gpu_hours + 1e-9:
            raise FillError(f"{lane.lane_id}: {lane.gpus} x {lane.minutes} min exceeds its cap")
    if lanes.TIMING_MINUTES / 60 > lanes.TIMING_CAP_GPU_HOURS + 1e-9:
        raise FillError("the timing job's minutes exceed its cap")


def check_small_lane_receipt(path: Path | None, preregistration_sha256: str,
                             repo_root: Path) -> dict[str, Any]:
    """The 4B lane waits on the 0.6B lane: a completed, job-bound receipt of this
    registration with smoke 452 REPRODUCED and v1's job-727 statistics
    reproduced (the registered validity gate). Never on its headroom read."""

    if path is None:
        raise FillError(f"{GATED_LANE} is filled only with --small-lane-receipt, the "
                        f"{GATING_LANE} lane's receipt (smoke 452 and job 727 reproduced)")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FillError(f"the {GATING_LANE} receipt is unreadable: {exc}") from exc
    if not isinstance(receipt, dict):
        raise FillError(f"the {GATING_LANE} receipt is not a JSON object")
    hashes = receipt.get("hashes") or {}
    lane = (receipt.get("lane") or {}).get("lane_id")
    if (receipt.get("experiment_id"), lane, receipt.get("profile"),
            receipt.get("status")) != (dv2.EXPERIMENT_ID, GATING_LANE, "registered",
                                       "PRECHECK_COMPLETE"):
        raise FillError(f"{path} is not a completed {GATING_LANE} receipt of "
                        f"{dv2.EXPERIMENT_ID}")
    if hashes.get("preregistration_sha256") != preregistration_sha256:
        raise FillError(f"{path} was read against another preregistration")
    if (not dv2.JOB_RE.fullmatch(str(receipt.get("slurm_job_id") or ""))
            or receipt.get("slurm_job_id_source") != "job.env"):
        raise FillError(f"{path} is not bound to its Slurm job")
    reproduction = (receipt.get("report") or {}).get("smoke_452_reproduction") or {}
    if reproduction.get("status") != "REPRODUCED":
        raise FillError(f"the {GATING_LANE} lane's K1 smoke reproduction is "
                        f"{reproduction.get('status')}: the combined read is INVALID and "
                        f"{GATED_LANE} is not run")
    gate = dv2.v1_reproduction(receipt, dv2.load_v1_small_lane_receipt(repo_root))
    if gate["status"] != "REPRODUCED":
        raise FillError(f"the {GATING_LANE} lane does not reproduce v1's job-727 receipt "
                        f"({gate['mismatch_count']} leaves differ, first "
                        f"{gate['mismatches'][:2]}): the combined read is INVALID and "
                        f"{GATED_LANE} is not run")
    return {"slurm_job_id": receipt.get("slurm_job_id"), "smoke_452": "REPRODUCED",
            "v1_job_727": "REPRODUCED"}


def _image_values(image_receipt: Path) -> dict[str, str]:
    receipt = json.loads(image_receipt.read_text(encoding="utf-8"))
    values = {"FILL-image-id": receipt["image_id"], "FILL-image-git-sha": receipt["git_sha"],
              "FILL-image-source-tar-sha256": receipt["source_tar_sha256"]}
    if not v1f.IMAGE_RE.fullmatch(values["FILL-image-id"]):
        raise FillError("image receipt image_id is not a local sha256 image id")
    if not v1f.GIT_RE.fullmatch(values["FILL-image-git-sha"]):
        raise FillError("image receipt git_sha is not 40 hex")
    if not v1f.SHA_RE.fullmatch(values["FILL-image-source-tar-sha256"]):
        raise FillError("image receipt source_tar_sha256 is not 64 hex")
    return values


def _filled_text(raw: str, values: dict[str, str]) -> str:
    text = raw
    for key, value in sorted(values.items(), key=lambda item: -len(item[0])):
        text = text.replace(f'"{key}"', f'"{value}"').replace(key, value)
    remaining = sorted(set(re.findall(r"FILL-[a-z0-9-]+", text)))
    if remaining:
        raise FillError(f"unfilled values remain: {remaining}")
    return text


def _write(output: Path, name: str, text: str) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    target = output / name
    if target.exists() and target.read_text(encoding="utf-8") != text:
        raise FillError(f"{target} exists with different content; never overwrite")
    return target


def check_timing_resources(manifest: dict[str, Any]) -> None:
    lane = lanes.LANES[lanes.TIMING_LANE]
    resources = manifest.get("resources") or {}
    command = manifest.get("command") or []
    if (resources.get("gpus"), resources.get("minutes"),
            (manifest.get("budget") or {}).get("max_gpu_hours"),
            manifest.get("container_profile")) != (lane.gpus, lanes.TIMING_MINUTES,
                                                   lanes.TIMING_CAP_GPU_HOURS,
                                                   lane.container_profile):
        raise FillError("the timing manifest's GPUs, minutes, cap or profile are not D36's")
    if ("--profile" not in command or command[command.index("--profile") + 1] != "timing"
            or "--preregistration" in command):
        raise FillError("the timing manifest must run --profile timing without a "
                        "preregistration")
    if "--lane" not in command or command[command.index("--lane") + 1] != lane.lane_id:
        raise FillError("the timing manifest runs another lane")
    model = manifest.get("model") or {}
    if (model.get("model_id"), model.get("revision"), model.get("receipt_sha256"),
            model.get("artifact_root_sha256")) != (lane.model_id, lane.revision,
                                                   lane.receipt_sha256,
                                                   lane.artifact_root_sha256):
        raise FillError("the timing manifest's model block is not the 4B lane's receipt")
    if manifest.get("seeds") != list(dhd.SEEDS):
        raise FillError(f"seeds must be {list(dhd.SEEDS)}")


def fill_timing(image_receipt: Path, output: Path, *, template_dir: Path = TEMPLATE_DIR,
                run_root: Path | None = None, job: int = 1) -> Path:
    """Development timing job ``job``'s manifest (before the freeze)."""

    if job not in TIMING_TEMPLATES:
        raise FillError(f"no development timing job {job!r}; jobs {sorted(TIMING_TEMPLATES)}")
    check_budget()
    values = _image_values(image_receipt)
    template = template_dir / TIMING_TEMPLATES[job]
    raw = template.read_text(encoding="utf-8")
    if sorted(set(re.findall(r"FILL-[a-z0-9-]+", raw))) != sorted(TIMING_VALUES):
        raise FillError("the timing template must hold exactly the three image values")
    text = _filled_text(raw, values)
    manifest = yaml.safe_load(text)
    v1f.check_against_template(manifest, yaml.safe_load(raw), values)
    check_timing_resources(manifest)
    run_root = run_root or Path(manifest["run_root"])
    if v1f.lane_jobs(run_root) or v1f.read_claims(run_root):
        raise FillError(f"{run_root} already holds timing job {job}; each timing run root "
                        f"allows one job (D36, D42)")
    plan = v1f.NextJob("first", lanes.TIMING_MINUTES, 0, None, 0)
    target = _write(output, template.name, text)
    v1f.claim_slot(run_root, lanes.LANES[lanes.TIMING_LANE], plan, text, values["FILL-image-id"])
    target.write_text(text, encoding="utf-8")
    return target


def fill(lane_id: str, image_receipt: Path, repo_root: Path, output: Path, *,
         template_dir: Path = TEMPLATE_DIR, continuation_of: str | None = None,
         run_root: Path | None = None, small_lane_receipt: Path | None = None) -> Path:
    if lane_id not in lanes.LANES:
        raise FillError(f"unknown registered lane {lane_id!r}")
    lane = lanes.LANES[lane_id]
    check_budget()
    values = _image_values(image_receipt)
    row = preregister.verify(dv2.EXPERIMENT_ID,
                             ledger=repo_root / "program" / "preregistrations" / "ledger.jsonl",
                             root=repo_root)
    values["FILL-preregistration-sha256"] = str(row["sha256"])
    if lane_id == GATED_LANE:
        check_small_lane_receipt(small_lane_receipt, str(row["sha256"]), repo_root)
    table = dict(v1f.IDENTITY_ROW_RE.findall(
        (repo_root / str(row["path"])).read_text(encoding="utf-8")))
    missing = [path for path in BOUND_PATHS if path not in table]
    if missing:
        raise FillError(f"the frozen preregistration does not table {missing}")
    for path, digest in table.items():
        if v1f._sha256(PROJECT_ROOT / path) != digest:
            raise FillError(f"{path} is not the code tabled in the frozen preregistration")
    template = template_dir / TEMPLATES[lane_id]
    if v1f._sha256(template) != table[f"{TEMPLATE_PREFIX}/{template.name}"]:
        raise FillError(f"{template} is not the tabled template")
    raw = template.read_text(encoding="utf-8")
    text = _filled_text(raw, values)
    manifest = yaml.safe_load(text)
    v1f.check_against_template(manifest, yaml.safe_load(raw), values)
    v1f.check_resources(manifest, lane, lane.minutes)
    v1f.check_image_commit(repo_root, values["FILL-image-git-sha"], row, table)
    run_root = run_root or Path(manifest["run_root"])
    plan = v1f.plan_next_job(lane, run_root, continuation_of)
    name = template.name
    if plan.kind != "first":
        manifest = v1f.later_job_manifest(manifest, plan)
        text = yaml.safe_dump(manifest, sort_keys=False)
        name = name.replace(".yaml", f"-{plan.kind}-after-{plan.slot}.yaml")
    target = _write(output, name, text)
    v1f.claim_slot(run_root, lane, plan, text, values["FILL-image-id"])  # every job, slot 0 too
    target.write_text(text, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--lane", choices=sorted(lanes.LANES), default=None)
    parser.add_argument("--timing", type=int, nargs="?", const=1, default=None,
                        choices=sorted(TIMING_TEMPLATES),
                        help="fill development timing job N (1: D36's, 2: D42's; before the "
                             "freeze)")
    parser.add_argument("--image-receipt", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--continuation-of", default=None)
    parser.add_argument("--run-root", type=Path, default=None,
                        help="the run root (default: the template's run_root)")
    parser.add_argument("--small-lane-receipt", type=Path, default=None,
                        help=f"for {GATED_LANE}: the {GATING_LANE} lane's receipt.json")
    args = parser.parse_args(argv)
    if (args.timing is not None) == (args.lane is not None):
        print("FAIL: give exactly one of --lane and --timing", file=sys.stderr)
        return 2
    try:
        if args.timing is not None:
            target = fill_timing(args.image_receipt, args.output, run_root=args.run_root,
                                 job=args.timing)
        else:
            target = fill(args.lane, args.image_receipt, args.repo_root, args.output,
                          continuation_of=args.continuation_of, run_root=args.run_root,
                          small_lane_receipt=args.small_lane_receipt)
    except (OSError, KeyError, ValueError, json.JSONDecodeError,
            preregister.PreregistrationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"filled": str(target),
                      "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
