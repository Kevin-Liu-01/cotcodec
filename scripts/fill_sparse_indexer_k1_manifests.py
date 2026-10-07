#!/usr/bin/env python3
"""Fill the Q3 K1 manifest templates from measured artifacts only.

Every ``FILL-*`` value in ``experiments/manifests/q3-k1-*.yaml`` is replaced by
a value read from a file that exists on disk: the image B build receipt
(image ID, git SHA, source-tar SHA-256), the bundle sidecar written by the
builder (bundle SHA-256 and size, re-hashed here from the bundle itself), the
commit that built the bundle (commit A), the frozen preregistration (its
SHA-256 must equal its ledger row) and, for the resumed legs, Slurm job ids
read from the predecessor run's ``job.env``. Nothing is typed by hand, so a
manifest can never carry a copied hash. Templates whose inputs are not yet
available (for example R2 before R1 has run) are skipped and reported.

Exit codes: 0 every requested manifest filled, 2 an input is missing or
inconsistent.
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

from scripts import preregister  # noqa: E402

TEMPLATES = PROJECT_ROOT / "experiments" / "manifests"
EXPERIMENT_ID = "q3-k1-localization-screen-v1"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
JOB_RE = re.compile(r"^[1-9][0-9]{0,19}$")


class FillError(ValueError):
    """An input needed to fill a manifest is missing or inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _job_id(run_root: Path) -> str:
    env = run_root.glob("*/job.env")
    for path in sorted(env):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("job_id="):
                value = line.split("=", 1)[1]
                if JOB_RE.fullmatch(value):
                    return value
    raise FillError(f"no job.env with a job id under {run_root}")


def measured_values(args: argparse.Namespace) -> dict[str, str]:
    receipt = json.loads(args.image_receipt.read_text(encoding="utf-8"))
    values = {
        "FILL-image-b-image-id": receipt["image_id"],
        "FILL-image-b-git-sha": receipt["git_sha"],
        "FILL-image-b-source-tar-sha256": receipt["source_tar_sha256"],
    }
    if not IMAGE_RE.fullmatch(values["FILL-image-b-image-id"]):
        raise FillError("image receipt image_id is not a local sha256 image id")
    if not GIT_RE.fullmatch(values["FILL-image-b-git-sha"]):
        raise FillError("image receipt git_sha is not 40 hex")
    if not SHA_RE.fullmatch(values["FILL-image-b-source-tar-sha256"]):
        raise FillError("image receipt source_tar_sha256 is not 64 hex")
    sidecar = json.loads(args.bundle_sidecar.read_text(encoding="utf-8"))
    actual = _sha256(args.bundle)
    if actual != sidecar["sha256"] or args.bundle.stat().st_size != sidecar["size_bytes"]:
        raise FillError("bundle on disk differs from its sidecar")
    values["FILL-bundle-sha256"] = actual
    values["FILL-bundle-size-bytes"] = str(sidecar["size_bytes"])
    if not GIT_RE.fullmatch(args.bundle_commit):
        raise FillError("--bundle-commit must be the 40-hex commit that built the bundle")
    values["FILL-commit-a-git-sha"] = args.bundle_commit
    ledger_root = args.repo_root
    row = preregister.verify(EXPERIMENT_ID, ledger=ledger_root / "program" / "preregistrations"
                             / "ledger.jsonl", root=ledger_root)
    values["FILL-preregistration-sha256"] = str(row["sha256"])
    if args.r1_run_root is not None:
        values["FILL-resume-r1-job-id"] = _job_id(args.r1_run_root)
    if args.main_run_root is not None:
        values["FILL-main-job-id"] = _job_id(args.main_run_root)
    return values


def fill_text(text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    for key, value in sorted(values.items(), key=lambda item: -len(item[0])):
        text = text.replace(f'"{key}"', f'"{value}"').replace(key, value)
    remaining = sorted(set(re.findall(r"FILL-[a-z0-9-]+", text)))
    return text, remaining


def fill_all(templates: list[Path], values: dict[str, str], output: Path) -> dict[str, Any]:
    report: dict[str, Any] = {"filled": [], "skipped": {}}
    output.mkdir(parents=True, exist_ok=True)
    for template in templates:
        text, remaining = fill_text(template.read_text(encoding="utf-8"), values)
        if remaining:
            report["skipped"][template.name] = remaining
            continue
        payload = yaml.safe_load(text)
        if payload["seeds"] != [int(v) for v in payload["command"][
                payload["command"].index("--seeds") + 1 : payload["command"].index("--seeds") + 4]]:
            raise FillError(f"{template.name}: argv seeds differ from declared seeds")
        target = output / template.name
        if target.exists() and target.read_text(encoding="utf-8") != text:
            raise FillError(f"{target} exists with different content; never overwrite")
        target.write_text(text, encoding="utf-8")
        report["filled"].append(str(target))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--image-receipt", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--bundle-sidecar", type=Path, required=True)
    parser.add_argument("--bundle-commit", required=True)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--r1-run-root", type=Path, default=None)
    parser.add_argument("--main-run-root", type=Path, default=None)
    parser.add_argument("--templates", type=Path, default=TEMPLATES)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        values = measured_values(args)
        report = fill_all(sorted(args.templates.glob("q3-k1-*.yaml")), values, args.output)
    except (OSError, KeyError, ValueError, json.JSONDecodeError,
            preregister.PreregistrationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
