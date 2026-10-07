#!/usr/bin/env python3
"""Fill the Q3 K1 manifest templates from measured artifacts only.

Every ``FILL-*`` value in ``experiments/manifests/q3-k1-*.yaml`` is replaced by
a value read from a file that exists on disk: the image B build receipt
(image ID, git SHA, source-tar SHA-256), the bundle sidecar written by the
builder (bundle SHA-256 and size, re-hashed here from the bundle itself), the
commit that built the bundle (commit A), the frozen preregistration (its
SHA-256 must equal its ledger row) and, for the resumed legs, the Slurm job id
of the predecessor. A resumed leg shares its predecessor's run root (the
lane's resume copy looks for ``<run_root>/<predecessor job id>``), and the
predecessor is chosen by what it did, never by sort order:

* R2 resumes the R1 job (manifest ``q3-k1-resume-r1``) whose
  ``termination.env`` says ``reason=signal_USR1_checkpoint_confirmed``,
  ``exit_code=75`` and ``checkpoint_ready=true``;
* ``q3-k1-main-resume`` continues the main job (``q3-k1-main``) that ended the
  same way, with ``minutes`` = 30 minus the minutes the interrupted job used
  (rounded up, plus one), filled only if at least 5 minutes remain;
* the extension resumes the main read: the ``q3-k1-main`` or
  ``q3-k1-main-resume`` job that ended ``reason=completed``, ``exit_code=0``
  and whose receipt names V1-failing ``extension_targets``.

More than one matching job is an error. Nothing is typed by hand, so a
manifest can never carry a copied hash. Templates whose inputs are not yet
available (for example R2 before R1 has run) are skipped and reported.

Exit codes: 0 every requested manifest filled, 2 an input is missing or
inconsistent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime
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
SIGNAL_CONFIRMED = {"reason": "signal_USR1_checkpoint_confirmed", "exit_code": "75",
                    "checkpoint_ready": "true"}
COMPLETED = {"reason": "completed", "exit_code": "0"}
MAIN_LIMIT_MINUTES = 30
MAIN_RESUME_MIN_MINUTES = 5
MAIN_GPUS = 4


class FillError(ValueError):
    """An input needed to fill a manifest is missing or inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _env_file(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator:
                fields[key] = value
    return fields


def _jobs(run_root: Path, names: set[str], ended: dict[str, str]) -> list[Path]:
    """Job directories under ``run_root`` from manifests ``names`` that ended as ``ended``."""

    matches: list[Path] = []
    if not run_root.is_dir():
        return matches
    for job_dir in sorted(run_root.iterdir()):
        if not job_dir.is_dir() or job_dir.is_symlink() or not JOB_RE.fullmatch(job_dir.name):
            continue
        job = _env_file(job_dir / "job.env")
        if job.get("job_id") != job_dir.name:
            continue
        try:
            manifest = json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("name") not in names:
            continue
        termination = _env_file(job_dir / "termination.env")
        if termination.get("job_id") != job_dir.name:
            continue
        if all(termination.get(key) == value for key, value in ended.items()):
            matches.append(job_dir)
    return matches


def _single(matches: list[Path], what: str) -> Path | None:
    if len(matches) > 1:
        raise FillError(f"{len(matches)} jobs qualify as {what}: "
                        + ", ".join(path.name for path in matches))
    return matches[0] if matches else None


def _minutes_used(job_dir: Path) -> int:
    started = _env_file(job_dir / "job.env")["started_at"]
    finished = _env_file(job_dir / "termination.env")["finished_at"]
    elapsed = (datetime.strptime(finished, "%Y-%m-%dT%H:%M:%SZ")
               - datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ")).total_seconds()
    if elapsed < 0:
        raise FillError(f"job {job_dir.name} finished before it started")
    return math.ceil(elapsed / 60.0) + 1  # +1: Slurm prolog before job.env was written


def predecessor_values(r1_run_root: Path | None, main_run_root: Path | None
                       ) -> tuple[dict[str, str], list[str]]:
    """Placeholder values for the resumed legs, and notes on legs that cannot run."""

    values: dict[str, str] = {}
    notes: list[str] = []
    if r1_run_root is not None:
        r1 = _single(_jobs(r1_run_root, {"q3-k1-resume-r1"}, SIGNAL_CONFIRMED),
                     "the signal-checkpointed R1")
        if r1 is None:
            notes.append("no R1 job ended with a confirmed USR1 checkpoint and exit 75")
        else:
            values["FILL-resume-r1-job-id"] = r1.name
    if main_run_root is not None:
        interrupted = _single(_jobs(main_run_root, {"q3-k1-main"}, SIGNAL_CONFIRMED),
                              "the signal-checkpointed main job")
        if interrupted is not None:
            remaining = MAIN_LIMIT_MINUTES - _minutes_used(interrupted)
            if remaining < MAIN_RESUME_MIN_MINUTES:
                notes.append(f"main job {interrupted.name} left {remaining} of "
                             f"{MAIN_LIMIT_MINUTES} minutes; no continuation within the cap")
            else:
                values["FILL-main-checkpointed-job-id"] = interrupted.name
                values["FILL-main-resume-minutes"] = str(remaining)
                values["FILL-main-resume-gpu-hours"] = (
                    f"{math.ceil(MAIN_GPUS * remaining / 60.0 * 100) / 100:.2f}")
        completed = _single(_jobs(main_run_root, {"q3-k1-main", "q3-k1-main-resume"},
                                  COMPLETED), "the completed main read")
        if completed is not None:
            receipt = json.loads((completed / "phase-0a-k1" / "receipt.json").read_text(
                encoding="utf-8"))
            if receipt.get("extension_targets"):
                values["FILL-main-job-id"] = completed.name
            else:
                notes.append(f"the main read ({receipt['verdict']['verdict']}) does not call "
                             "for the V1 extension")
    return values, notes


def measured_values(args: argparse.Namespace) -> tuple[dict[str, str], list[str]]:
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
    resumed, notes = predecessor_values(args.r1_run_root, args.main_run_root)
    values.update(resumed)
    return values, notes


def fill_text(text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    for key, value in sorted(values.items(), key=lambda item: -len(item[0])):
        text = text.replace(f'"{key}"', f'"{value}"').replace(key, value)
    remaining = sorted(set(re.findall(r"FILL-[a-z0-9-]+", text)))
    return text, remaining


def fill_all(templates: list[Path], values: dict[str, str], output: Path,
             notes: list[str] | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {"filled": [], "skipped": {}, "notes": list(notes or [])}
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
        values, notes = measured_values(args)
        report = fill_all(sorted(args.templates.glob("q3-k1-*.yaml")), values, args.output,
                          notes)
    except (OSError, KeyError, ValueError, json.JSONDecodeError,
            preregister.PreregistrationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
