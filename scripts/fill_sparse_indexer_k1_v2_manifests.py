#!/usr/bin/env python3
"""Fill the K1 successor's manifest templates from measured artifacts only.

The v2 counterpart of ``scripts/fill_sparse_indexer_k1_manifests.py`` (v1,
unchanged); it enforces the same gates and adds the probe-derived limits.
Every ``FILL-*`` value in ``experiments/manifests/q3-k1-v2/q3-k1-v2-*.yaml`` is
replaced by a value read from a file that exists on disk:

* the v2 image B build receipt (image ID, git SHA, source-tar SHA-256);
* the v1 bundle and its sidecar (re-hashed here and compared with the digest
  stated in the frozen v2 preregistration; no rebuild), and the commit that
  built it (v1's commit A, stated in the registration);
* the frozen v2 preregistration (its SHA-256 must equal its ledger row; its
  code table must hold this filler's and the resume comparison's digests);
* the job limits: the contract's ``execution.job_limits``. The contract must
  be the tabled one, the limits must equal what the registered formula
  (``harness/sparse_indexer_k1_budget_v2.derive_limits``) gives for the rates
  of the throughput probe receipt passed with ``--probe-receipt``, whose
  SHA-256 the registration states, and the probe must have measured the code
  tabled here. Nothing about the limits is typed by hand;
* for the resumed legs, the Slurm job id of the predecessor, chosen by what it
  did (v1's rules): R2 resumes the signal-checkpointed R1; the main job's one
  continuation resumes a signal-checkpointed main job with the main limit minus
  the minutes it used (only if at least 5 remain, and never a second time); the
  extension resumes the completed main read that names V1-failing
  ``extension_targets`` (never a second time).

The main job, its continuation and the extension are filled only after the
pre-main gates pass (program decisions D16 and D20): exactly one completed
smoke job whose receipt is ``SMOKE_PASS`` with every gate true and whose
measured rates, recomputed here with the registered formula, put both the main
job and the worst-case V1 extension within their limits; exactly one completed
development headroom job whose receipt is ``PROCEED_TO_K1`` under the
registered H1, H2a and H2b rules; and an equivalent resume test (R0 completed,
R1 signal-checkpointed, R2 completed from that R1, and
``scripts/compare_sparse_indexer_resume.py`` equivalent). Every gate job must
have run under the v2 image B and the bundle, and its receipt must carry this
experiment id, the registered profile, the frozen preregistration's digest and
the tabled code and contract digests. Nothing overrides a failed gate.

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

from harness import sparse_indexer_k1_budget_v2 as budget  # noqa: E402
from harness import sparse_indexer_k1_stats as k1s  # noqa: E402
from scripts import preregister  # noqa: E402
from scripts.compare_sparse_indexer_resume import compare  # noqa: E402

TEMPLATES = PROJECT_ROOT / "experiments" / "manifests" / "q3-k1-v2"
EXPERIMENT_ID = "q3-k1-localization-screen-v2"
PROBE_ID = "q3-k1-throughput-probe-v1"
PREFIX = "q3-k1-v2-"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
JOB_RE = re.compile(r"^[1-9][0-9]{0,19}$")
SIGNAL_CONFIRMED = {"reason": "signal_USR1_checkpoint_confirmed", "exit_code": "75",
                    "checkpoint_ready": "true"}
COMPLETED = {"reason": "completed", "exit_code": "0"}
MAIN_GPUS = budget.MAIN_GPUS
MAIN_READ_TEMPLATES = (f"{PREFIX}main", f"{PREFIX}main-resume", f"{PREFIX}extension")
CONTRACT_PATH = "experiments/architectures/translation-supervised-sparse-indexer-k1-screen-v2.yaml"
SELF_PATHS = ("scripts/fill_sparse_indexer_k1_v2_manifests.py",
              "scripts/compare_sparse_indexer_resume.py")
IDENTITY_ROW_RE = re.compile(r"^\| ([A-Za-z0-9_./-]+\.(?:py|yaml)) \| ([0-9a-f]{64}) \|$", re.M)
BUNDLE_ROW_RE = re.compile(r"^\| k1-bundle-v1\.json SHA-256 \| ([0-9a-f]{64}) \|$", re.M)
BUNDLE_COMMIT_ROW_RE = re.compile(r"^\| k1-bundle-v1\.json built at commit \| ([0-9a-f]{40}) \|$",
                                  re.M)
PROBE_ROW_RE = re.compile(
    r"^\| q3-k1-throughput-probe-v1 receipt SHA-256 \| ([0-9a-f]{64}) \|$", re.M)


class FillError(ValueError):
    """An input needed to fill a manifest is missing or inconsistent."""


@dataclass(frozen=True)
class Identity:
    """What every v2 GPU job must have run under."""

    image_id: str
    git_sha: str
    source_sha256: str
    bundle_sha256: str
    preregistration_sha256: str
    code: dict[str, str]  # tabled file -> SHA-256, from the frozen preregistration


@dataclass(frozen=True)
class Registered:
    """What the frozen v2 preregistration states."""

    code: dict[str, str]
    bundle_sha256: str
    bundle_commit: str
    probe_receipt_sha256: str


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
    matches: list[Path] = []
    for job_dir in _named_jobs(run_root, names):
        if _env_file(job_dir / "job.env").get("job_id") != job_dir.name:
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


def predecessor_values(r1_run_root: Path | None, main_run_root: Path | None,
                       main_limit: int) -> tuple[dict[str, str], list[str]]:
    """Placeholder values for the resumed legs, and notes on legs that cannot run."""

    values: dict[str, str] = {}
    notes: list[str] = []
    if r1_run_root is not None:
        r1 = _single(_jobs(r1_run_root, {f"{PREFIX}resume-r1"}, SIGNAL_CONFIRMED),
                     "the signal-checkpointed R1")
        if r1 is None:
            notes.append("no R1 job ended with a confirmed USR1 checkpoint and exit 75")
        else:
            values["FILL-resume-r1-job-id"] = r1.name
    if main_run_root is not None:
        interrupted = _single(_jobs(main_run_root, {f"{PREFIX}main"}, SIGNAL_CONFIRMED),
                              "the signal-checkpointed main job")
        continued = _named_jobs(main_run_root, {f"{PREFIX}main-resume"})
        if interrupted is not None and continued:
            notes.append("the continuation already ran (job "
                         + ", ".join(job.name for job in continued)
                         + "); a second continuation is declined (program decision D16)")
        elif interrupted is not None:
            used = _minutes_used(interrupted)
            remaining = budget.continuation_minutes(main_limit, used)
            if remaining is None:
                notes.append(f"main job {interrupted.name} left {main_limit - used} of "
                             f"{main_limit} minutes; no continuation within the cap")
            else:
                values["FILL-main-checkpointed-job-id"] = interrupted.name
                values["FILL-main-resume-minutes"] = str(remaining)
                values["FILL-main-resume-gpu-hours"] = (
                    f"{budget.gpu_hours(MAIN_GPUS, remaining):.2f}")
        completed = _single(_jobs(main_run_root, {f"{PREFIX}main", f"{PREFIX}main-resume"},
                                  COMPLETED), "the completed main read")
        if completed is not None:
            receipt = json.loads((completed / "phase-0a-k1" / "receipt.json").read_text(
                encoding="utf-8"))
            extended = _named_jobs(main_run_root, {f"{PREFIX}extension"})
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


def registered_identity(prereg: Path) -> Registered:
    """The code table, bundle digest and commit, and probe receipt digest of the registration."""

    text = prereg.read_text(encoding="utf-8")
    code = dict(IDENTITY_ROW_RE.findall(text))
    if CONTRACT_PATH not in code or not all(path in code for path in SELF_PATHS):
        raise FillError("the frozen preregistration lacks its code digest table")
    found = {}
    for name, pattern in (("bundle", BUNDLE_ROW_RE), ("bundle commit", BUNDLE_COMMIT_ROW_RE),
                          ("probe receipt", PROBE_ROW_RE)):
        rows = pattern.findall(text)
        if len(rows) != 1:
            raise FillError(f"the frozen preregistration must state exactly one {name} digest")
        found[name] = rows[0]
    return Registered(code, found["bundle"], found["bundle commit"], found["probe receipt"])


def registered_limits(repo_root: Path, registered: Registered, probe_receipt: Path | None
                      ) -> dict[str, dict[str, float]]:
    """The contract's job limits, checked against the registered formula and the probe."""

    contract_path = repo_root / CONTRACT_PATH
    if _sha256(contract_path) != registered.code[CONTRACT_PATH]:
        raise FillError("the contract is not the one tabled in the frozen preregistration")
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    limits = contract.get("execution", {}).get("job_limits")
    if not isinstance(limits, dict):
        raise FillError("the contract's job limits are not set (they come from the "
                        f"{PROBE_ID} receipt)")
    try:
        table = budget.check_limits(limits)
    except budget.BudgetContractError as exc:
        raise FillError(f"the contract's job limits are invalid: {exc}") from exc
    if probe_receipt is None:
        raise FillError("--probe-receipt is required: the limits are checked against it")
    if _sha256(probe_receipt) != registered.probe_receipt_sha256:
        raise FillError("the probe receipt is not the one the preregistration states")
    receipt = json.loads(probe_receipt.read_text(encoding="utf-8"))
    if receipt.get("experiment_id") != PROBE_ID or receipt.get("status") != "PROBE_COMPLETE":
        raise FillError("the probe receipt is not a complete q3-k1-throughput-probe-v1 receipt")
    if receipt.get("profile") != "registered":
        raise FillError("the probe receipt is not from the registered profile")
    measured = receipt.get("hashes", {}).get("code", {})
    for path, digest in measured.items():
        if path in registered.code and registered.code[path] != digest:
            raise FillError(f"the probe measured another version of {path}")
    derived = budget.limits_table(budget.derive_limits(budget.Rates.from_dict(receipt["rates"])))
    if derived != table:
        raise FillError("the contract's job limits are not the registered formula's limits for "
                        "the probe's rates")
    if budget.derive_limits(budget.Rates.from_dict(receipt["rates"]))["gauntlet_required"]:
        raise FillError("the probe-derived caps exceed 8 GPU-h: the gauntlet applies "
                        "(program decision D20)")
    return table


def _receipt(job_dir: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads((job_dir / "phase-0a-k1" / "receipt.json").read_text(
            encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _bound(job_dir: Path, identity: Identity, receipt: dict[str, Any] | None,
           phase: str | None) -> list[str]:
    """Reasons a gate job did not run under the registered identity (empty if it did)."""

    problems: list[str] = []
    job = _env_file(job_dir / "job.env")
    expected = {"image_id": identity.image_id, "git_sha": identity.git_sha,
                "source_sha256": identity.source_sha256,
                "study_artifact_sha256": identity.bundle_sha256}
    for key, value in expected.items():
        if job.get(key) != value:
            problems.append(f"job {job_dir.name}: job.env {key} is not the v2 image B's or "
                            "the bundle's")
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


def smoke_gate(run_root: Path | None, identity: Identity,
               limits: dict[str, dict[str, float]]) -> dict[str, Any]:
    """SMOKE_PASS: every gate true, and the main job and the worst-case extension fit their
    limits under the smoke's measured rates (recomputed with the registered formula)."""

    if run_root is None:
        return _gate(["no --smoke-run-root was given"])
    try:
        job = _single(_jobs(run_root, {f"{PREFIX}smoke"}, COMPLETED), "the completed smoke job")
    except FillError as exc:
        return _gate([str(exc)])
    if job is None:
        return _gate([f"no {PREFIX}smoke job ended completed with exit code 0"])
    receipt = _receipt(job)
    problems = _bound(job, identity, receipt, "smoke")
    if receipt is not None:
        if receipt.get("status") != "SMOKE_PASS":
            problems.append(f"smoke status is {receipt.get('status')}, not SMOKE_PASS")
        gates = receipt.get("gates")
        if not (isinstance(gates, dict) and gates and all(v is True for v in gates.values())):
            problems.append("not every smoke gate is true")
        try:
            rates = budget.Rates.from_dict(receipt["projection"]["rates"])
            recomputed = budget.smoke_gate(rates, limits)
        except (KeyError, TypeError, ValueError, budget.BudgetContractError) as exc:
            problems.append(f"the smoke's rates are unreadable: {exc}")
        else:
            for name in ("main", "extension"):
                part = recomputed[name]
                if not part["fits"]:
                    problems.append(f"{name}: 1.2 x projected wall + 3 min is "
                                    f"{part['required_limit_minutes']:.2f}, over "
                                    f"{part['limit_minutes']} min")
    return _gate(problems, job_id=job.name)


def headroom_dev_gate(run_root: Path | None, identity: Identity) -> dict[str, Any]:
    """PROCEED_TO_K1, recomputed with the registered H1, H2a and H2b rules."""

    if run_root is None:
        return _gate(["no --headroom-dev-run-root was given"])
    try:
        job = _single(_jobs(run_root, {f"{PREFIX}headroom-dev"}, COMPLETED),
                      "the completed development headroom job")
    except FillError as exc:
        return _gate([str(exc)])
    if job is None:
        return _gate([f"no {PREFIX}headroom-dev job ended completed with exit code 0"])
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
        r0 = _single(_jobs(r0_run_root, {f"{PREFIX}resume-r0"}, COMPLETED), "the completed R0")
        r1 = _single(_jobs(r1_run_root, {f"{PREFIX}resume-r1"}, SIGNAL_CONFIRMED),
                     "the signal-checkpointed R1")
        r2 = _single(_jobs(r1_run_root, {f"{PREFIX}resume-r2"}, COMPLETED), "the completed R2")
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
        "FILL-image-b2-image-id": receipt["image_id"],
        "FILL-image-b2-git-sha": receipt["git_sha"],
        "FILL-image-b2-source-tar-sha256": receipt["source_tar_sha256"],
    }
    if not IMAGE_RE.fullmatch(values["FILL-image-b2-image-id"]):
        raise FillError("image receipt image_id is not a local sha256 image id")
    if not GIT_RE.fullmatch(values["FILL-image-b2-git-sha"]):
        raise FillError("image receipt git_sha is not 40 hex")
    if not SHA_RE.fullmatch(values["FILL-image-b2-source-tar-sha256"]):
        raise FillError("image receipt source_tar_sha256 is not 64 hex")
    sidecar = json.loads(args.bundle_sidecar.read_text(encoding="utf-8"))
    actual = _sha256(args.bundle)
    if actual != sidecar["sha256"] or args.bundle.stat().st_size != sidecar["size_bytes"]:
        raise FillError("bundle on disk differs from its sidecar")
    values["FILL-bundle-sha256"] = actual
    values["FILL-bundle-size-bytes"] = str(sidecar["size_bytes"])
    ledger_root = args.repo_root
    row = preregister.verify(EXPERIMENT_ID, ledger=ledger_root / "program" / "preregistrations"
                             / "ledger.jsonl", root=ledger_root)
    values["FILL-preregistration-sha256"] = str(row["sha256"])
    registered = registered_identity(ledger_root / str(row["path"]))
    if actual != registered.bundle_sha256:
        raise FillError("the bundle differs from the SHA-256 stated in the frozen "
                        "preregistration")
    if args.bundle_commit != registered.bundle_commit:
        raise FillError("--bundle-commit is not the commit the preregistration says built "
                        "the bundle")
    values["FILL-bundle-commit-git-sha"] = registered.bundle_commit
    for path in SELF_PATHS:
        if _sha256(PROJECT_ROOT / path) != registered.code[path]:
            raise FillError(f"{path} is not the code tabled in the frozen preregistration")
    limits = registered_limits(ledger_root, registered, args.probe_receipt)
    for job, entry in limits.items():
        values[f"FILL-limit-{job}-minutes"] = str(entry["minutes"])
        values[f"FILL-limit-{job}-gpu-hours"] = f"{entry['max_gpu_hours']:.2f}"
    identity = Identity(values["FILL-image-b2-image-id"], values["FILL-image-b2-git-sha"],
                        values["FILL-image-b2-source-tar-sha256"], actual, str(row["sha256"]),
                        registered.code)
    resumed, notes = predecessor_values(args.r1_run_root, args.main_run_root,
                                        int(limits["main"]["minutes"]))
    values.update(resumed)
    gates = {"smoke": smoke_gate(args.smoke_run_root, identity, limits),
             "headroom_dev": headroom_dev_gate(args.headroom_dev_run_root, identity),
             "resume_equivalence": resume_gate(args.r0_run_root, args.r1_run_root, identity)}
    return values, notes, gates


def blocked_templates(gates: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
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
        start = payload["command"].index("--seeds") + 1
        if payload["seeds"] != [int(v) for v in payload["command"][start : start + 3]]:
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
    parser.add_argument("--probe-receipt", type=Path, default=None)
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
        report = fill_all(sorted(args.templates.glob(f"{PREFIX}*.yaml")), values, args.output,
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
