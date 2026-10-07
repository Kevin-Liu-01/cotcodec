#!/usr/bin/env python3
"""Fill the Q3 K1 manifest templates from measured artifacts only.

Every ``FILL-*`` value in ``experiments/manifests/q3-k1-*.yaml`` is replaced by
a value read from a file that exists on disk: the image B build receipt
(image ID, git SHA, source-tar SHA-256), the bundle sidecar written by the
builder (bundle SHA-256 and size, re-hashed here from the bundle itself and
compared with the digest stated in the frozen preregistration), the commit
that built the bundle (commit A), the frozen preregistration (its SHA-256 must
equal its ledger row) and, for the resumed legs, the Slurm job id of the
predecessor. The filler and the resume comparison it runs must carry the
SHA-256 digests tabled in the frozen preregistration. A resumed leg shares its
predecessor's run root (the lane's resume copy looks for
``<run_root>/<predecessor job id>``), and the predecessor is chosen by what it
did, never by sort order:

* R2 resumes the R1 job (manifest ``q3-k1-resume-r1``) whose
  ``termination.env`` says ``reason=signal_USR1_checkpoint_confirmed``,
  ``exit_code=75`` and ``checkpoint_ready=true``;
* ``q3-k1-main-resume`` continues the main job (``q3-k1-main``) that ended the
  same way, with ``minutes`` = 30 minus the minutes the interrupted job used
  (rounded up, plus one), filled only if at least 5 minutes remain and the run
  root holds no continuation job yet (a second continuation is declined,
  program decision D16);
* the extension resumes the main read: the ``q3-k1-main`` or
  ``q3-k1-main-resume`` job that ended ``reason=completed``, ``exit_code=0``
  and whose receipt names V1-failing ``extension_targets``, filled only while
  the run root holds no extension job (no second extension, D16).

The main job, its continuation and the extension (the main-read manifests) are
filled only after the registered pre-main gates pass (program decision D16):
exactly one completed smoke job whose receipt is ``SMOKE_PASS`` (all gates
true, 1.2 x the projected wall time + 3 minutes within 30 minutes), exactly one
completed development headroom job whose receipt is ``PROCEED_TO_K1`` under the
registered H1, H2a and H2b rules, and an equivalent resume test (R0 completed,
R1 signal-checkpointed, R2 completed from that R1, and
``scripts/compare_sparse_indexer_resume.py`` equivalent). Every gate job must
have run under image B and the bundle, and its receipt must carry this
experiment id, the registered profile, the frozen preregistration's digest and
the tabled code and contract digests. A failed or missing gate blocks the
main-read manifests and is reported; nothing overrides it.

More than one matching predecessor job is an error. Nothing is typed by hand,
so a manifest can never carry a copied hash. Templates whose inputs are not yet
available (for example R2 before R1 has run) are skipped and reported.

Exit codes: 0 every manifest whose inputs exist and whose gates pass was
filled (the report lists skipped and blocked templates), 2 an input is missing
or inconsistent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import sparse_indexer_k1_stats as k1s  # noqa: E402
from scripts import preregister  # noqa: E402
from scripts.compare_sparse_indexer_resume import compare  # noqa: E402

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
PROJECTION_MARGIN = 1.2  # the registered smoke gate: 1.2 x projected wall + the 3-minute USR1 lead
SIGNAL_LEAD_MINUTES = 3.0
MAIN_READ_TEMPLATES = ("q3-k1-main", "q3-k1-main-resume", "q3-k1-extension")
CONTRACT_PATH = "experiments/architectures/translation-supervised-sparse-indexer-k1-screen.yaml"
SELF_PATHS = ("scripts/fill_sparse_indexer_k1_manifests.py",
              "scripts/compare_sparse_indexer_resume.py")
IDENTITY_ROW_RE = re.compile(r"^\| ([A-Za-z0-9_./-]+\.(?:py|yaml)) \| ([0-9a-f]{64}) \|$", re.M)
BUNDLE_ROW_RE = re.compile(r"^\| k1-bundle-v1\.json SHA-256 \| ([0-9a-f]{64}) \|$", re.M)


class FillError(ValueError):
    """An input needed to fill a manifest is missing or inconsistent."""


@dataclass(frozen=True)
class Identity:
    """What every K1 GPU job must have run under."""

    image_id: str
    git_sha: str
    source_sha256: str
    bundle_sha256: str
    preregistration_sha256: str
    code: dict[str, str]  # tabled file -> SHA-256, from the frozen preregistration


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


def _named_jobs(run_root: Path, names: set[str]) -> list[Path]:
    """Job directories under ``run_root`` whose lane manifest is one of ``names``, however
    (or whether) they ended."""

    matches: list[Path] = []
    if not run_root.is_dir():
        return matches
    for job_dir in sorted(run_root.iterdir()):
        if not job_dir.is_dir() or job_dir.is_symlink() or not JOB_RE.fullmatch(job_dir.name):
            continue
        try:
            manifest = json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(manifest, dict) and manifest.get("name") in names:
            matches.append(job_dir)
    return matches


def _jobs(run_root: Path, names: set[str], ended: dict[str, str]) -> list[Path]:
    """Job directories under ``run_root`` from manifests ``names`` that ended as ``ended``."""

    matches: list[Path] = []
    for job_dir in _named_jobs(run_root, names):
        job = _env_file(job_dir / "job.env")
        if job.get("job_id") != job_dir.name:
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
        continued = _named_jobs(main_run_root, {"q3-k1-main-resume"})
        if interrupted is not None and continued:
            notes.append("the continuation already ran (job "
                         + ", ".join(job.name for job in continued)
                         + "); a second continuation is declined (program decision D16)")
        elif interrupted is not None:
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
            extended = _named_jobs(main_run_root, {"q3-k1-extension"})
            if receipt.get("extension_targets") and extended:
                notes.append("the extension already ran (job "
                             + ", ".join(job.name for job in extended)
                             + "); no second extension runs (program decision D16)")
            elif receipt.get("extension_targets"):
                values["FILL-main-job-id"] = completed.name
            else:
                notes.append(f"the main read ({receipt['verdict']['verdict']}) does not call "
                             "for the V1 extension")
    return values, notes


def registered_identity(prereg: Path) -> tuple[dict[str, str], str]:
    """The code digest table and the bundle SHA-256 stated in the frozen preregistration."""

    text = prereg.read_text(encoding="utf-8")
    code = dict(IDENTITY_ROW_RE.findall(text))
    bundles = BUNDLE_ROW_RE.findall(text)
    if CONTRACT_PATH not in code or not all(path in code for path in SELF_PATHS):
        raise FillError("the frozen preregistration lacks its code digest table")
    if len(bundles) != 1:
        raise FillError("the frozen preregistration must state exactly one bundle SHA-256")
    return code, bundles[0]


def _receipt(job_dir: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads((job_dir / "phase-0a-k1" / "receipt.json").read_text(
            encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _bound(job_dir: Path, identity: Identity, receipt: dict[str, Any] | None,
           phase: str | None) -> list[str]:
    """Reasons a gate job did not run under the registered identity (empty if it did).

    ``receipt`` None checks the lane's ``job.env`` only (R1 ends with exit 75 and
    writes no receipt)."""

    problems: list[str] = []
    job = _env_file(job_dir / "job.env")
    expected = {"image_id": identity.image_id, "git_sha": identity.git_sha,
                "source_sha256": identity.source_sha256,
                "study_artifact_sha256": identity.bundle_sha256}
    for key, value in expected.items():
        if job.get(key) != value:
            problems.append(f"job {job_dir.name}: job.env {key} is not image B's or the bundle's")
    if phase is None:
        return problems
    if receipt is None:
        return [*problems, f"job {job_dir.name}: phase-0a-k1/receipt.json is unreadable"]
    hashes = receipt.get("hashes") if isinstance(receipt.get("hashes"), dict) else {}
    code = hashes.get("code") if isinstance(hashes.get("code"), dict) else {}
    checks = {
        "experiment_id": receipt.get("experiment_id") == EXPERIMENT_ID,
        "phase": receipt.get("phase") == phase,
        "profile": receipt.get("profile") == "registered",
        "preregistration digest": (hashes.get("preregistration_sha256")
                                   == identity.preregistration_sha256),
        "bundle digest": hashes.get("bundle_sha256") == identity.bundle_sha256,
        "contract digest": hashes.get("contract_sha256") == identity.code[CONTRACT_PATH],
        "code digests": bool(code) and all(identity.code.get(name) == digest
                                           for name, digest in code.items()),
    }
    problems.extend(f"job {job_dir.name}: receipt {name} is not the registered one"
                    for name, ok in checks.items() if not ok)
    return problems


def _gate(problems: list[str], **detail: Any) -> dict[str, Any]:
    return {"passed": not problems, "problems": problems, **detail}


def smoke_gate(run_root: Path | None, identity: Identity) -> dict[str, Any]:
    """SMOKE_PASS: every smoke gate true and 1.2 x projected wall + 3 min <= 30 min."""

    if run_root is None:
        return _gate(["no --smoke-run-root was given"])
    try:
        job = _single(_jobs(run_root, {"q3-k1-smoke"}, COMPLETED), "the completed smoke job")
    except FillError as exc:
        return _gate([str(exc)])
    if job is None:
        return _gate(["no q3-k1-smoke job ended completed with exit code 0"])
    receipt = _receipt(job)
    problems = _bound(job, identity, receipt, "smoke")
    if receipt is not None:
        if receipt.get("status") != "SMOKE_PASS":
            problems.append(f"smoke status is {receipt.get('status')}, not SMOKE_PASS")
        gates = receipt.get("gates")
        if not (isinstance(gates, dict) and gates and all(v is True for v in gates.values())):
            problems.append("not every smoke gate is true")
        projection = receipt.get("projection")
        try:
            required = (PROJECTION_MARGIN * float(projection["main_wall_minutes"])
                        + SIGNAL_LEAD_MINUTES)
        except (KeyError, TypeError, ValueError):
            required = math.inf
        if not required <= MAIN_LIMIT_MINUTES:
            problems.append(f"1.2 x projected wall + 3 min is {required:.2f}, over "
                            f"{MAIN_LIMIT_MINUTES} min")
    return _gate(problems, job_id=job.name)


def headroom_dev_gate(run_root: Path | None, identity: Identity) -> dict[str, Any]:
    """PROCEED_TO_K1, recomputed with the registered H1, H2a and H2b rules."""

    if run_root is None:
        return _gate(["no --headroom-dev-run-root was given"])
    try:
        job = _single(_jobs(run_root, {"q3-k1-headroom-dev"}, COMPLETED),
                      "the completed development headroom job")
    except FillError as exc:
        return _gate([str(exc)])
    if job is None:
        return _gate(["no q3-k1-headroom-dev job ended completed with exit code 0"])
    receipt = _receipt(job)
    problems = _bound(job, identity, receipt, "headroom-dev")
    if receipt is not None:
        if (receipt.get("status") != "HEADROOM_DEV_COMPLETE"
                or receipt.get("decision") != "PROCEED_TO_K1"):
            problems.append(f"development headroom decision is {receipt.get('decision')}, "
                            "not PROCEED_TO_K1")
        try:
            read = k1s.HeadroomRead(float(receipt["h1_points"]),
                                    k1s.Interval.from_dict(receipt["h2a"]),
                                    k1s.Interval.from_dict(receipt["h2b"]))
            proceed = read.h1_interpretable and read.h2a_pass and read.h2b_pass
        except (KeyError, TypeError, ValueError):
            proceed = False
        if not proceed:
            problems.append("the registered H1, H2a and H2b rules do not give PROCEED_TO_K1")
    return _gate(problems, job_id=job.name)


def resume_gate(r0_run_root: Path | None, r1_run_root: Path | None,
                identity: Identity) -> dict[str, Any]:
    """R2 (resumed from the signal-checkpointed R1) equals R0 bit for bit."""

    if r0_run_root is None or r1_run_root is None:
        return _gate(["the resume test needs --r0-run-root and --r1-run-root"])
    try:
        r0 = _single(_jobs(r0_run_root, {"q3-k1-resume-r0"}, COMPLETED), "the completed R0")
        r1 = _single(_jobs(r1_run_root, {"q3-k1-resume-r1"}, SIGNAL_CONFIRMED),
                     "the signal-checkpointed R1")
        r2 = _single(_jobs(r1_run_root, {"q3-k1-resume-r2"}, COMPLETED), "the completed R2")
    except FillError as exc:
        return _gate([str(exc)])
    legs = {"R0 (completed)": r0, "R1 (signal-checkpointed, exit 75)": r1,
            "R2 (completed)": r2}
    missing = [name for name, job in legs.items() if job is None]
    if missing:
        return _gate([f"no {name} job" for name in missing])
    assert r0 is not None and r1 is not None and r2 is not None
    problems = [*_bound(r0, identity, _receipt(r0), "resume-test"),
                *_bound(r1, identity, None, None),
                *_bound(r2, identity, _receipt(r2), "resume-test")]
    if _env_file(r2 / "job.env").get("predecessor_job_id") != r1.name:
        problems.append(f"R2 job {r2.name} did not resume from R1 job {r1.name}")
    try:
        report = compare(r0, r1, r2)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        problems.append(f"the resume comparison could not read its inputs: {exc}")
    else:
        if not report["equivalent"]:
            failed = sorted(name for name, ok in report["checks"].items() if not ok)
            problems.append("the resume test is not equivalent: " + ", ".join(failed))
    return _gate(problems, job_ids={"r0": r0.name, "r1": r1.name, "r2": r2.name})


def measured_values(args: argparse.Namespace
                    ) -> tuple[dict[str, str], list[str], dict[str, dict[str, Any]]]:
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
    code, stated_bundle = registered_identity(ledger_root / str(row["path"]))
    if actual != stated_bundle:
        raise FillError("the bundle differs from the SHA-256 stated in the frozen "
                        "preregistration")
    for path in SELF_PATHS:
        if _sha256(PROJECT_ROOT / path) != code[path]:
            raise FillError(f"{path} is not the code tabled in the frozen preregistration")
    identity = Identity(values["FILL-image-b-image-id"], values["FILL-image-b-git-sha"],
                        values["FILL-image-b-source-tar-sha256"], actual, str(row["sha256"]),
                        code)
    resumed, notes = predecessor_values(args.r1_run_root, args.main_run_root)
    values.update(resumed)
    gates = {"smoke": smoke_gate(args.smoke_run_root, identity),
             "headroom_dev": headroom_dev_gate(args.headroom_dev_run_root, identity),
             "resume_equivalence": resume_gate(args.r0_run_root, args.r1_run_root, identity)}
    return values, notes, gates


def blocked_templates(gates: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Main-read templates the failed pre-main gates hold back, with the reasons."""

    reasons = [f"{name}: {problem}" for name, gate in gates.items() if not gate["passed"]
               for problem in gate["problems"]]
    return {name: reasons for name in MAIN_READ_TEMPLATES} if reasons else {}


def fill_text(text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    for key, value in sorted(values.items(), key=lambda item: -len(item[0])):
        text = text.replace(f'"{key}"', f'"{value}"').replace(key, value)
    remaining = sorted(set(re.findall(r"FILL-[a-z0-9-]+", text)))
    return text, remaining


def fill_all(templates: list[Path], values: dict[str, str], output: Path,
             notes: list[str] | None = None,
             blocked: dict[str, list[str]] | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {"filled": [], "skipped": {}, "blocked": {},
                              "notes": list(notes or [])}
    output.mkdir(parents=True, exist_ok=True)
    for template in templates:
        if template.stem in (blocked or {}):
            report["blocked"][template.name] = list((blocked or {})[template.stem])
            continue
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
    parser.add_argument("--smoke-run-root", type=Path, default=None)
    parser.add_argument("--headroom-dev-run-root", type=Path, default=None)
    parser.add_argument("--r0-run-root", type=Path, default=None)
    parser.add_argument("--r1-run-root", type=Path, default=None,
                        help="the run root of R1 and R2")
    parser.add_argument("--main-run-root", type=Path, default=None)
    parser.add_argument("--templates", type=Path, default=TEMPLATES)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        values, notes, gates = measured_values(args)
        report = fill_all(sorted(args.templates.glob("q3-k1-*.yaml")), values, args.output,
                          notes, blocked_templates(gates))
        report["pre_main_gates"] = gates
    except (OSError, KeyError, ValueError, json.JSONDecodeError,
            preregister.PreregistrationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
