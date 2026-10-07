#!/usr/bin/env python3
"""Fill the K1 throughput probe's manifest template from measured artifacts only.

``experiments/manifests/q3-k1-throughput-probe-v1/q3-k1-throughput-probe.yaml``
has four ``FILL-*`` values: the probe image's ID, git SHA and source-tar SHA-256
(from its build receipt) and the frozen probe preregistration's SHA-256 (which
must equal its ledger row). The filler refuses to run unless its own digest
and the probe code's digests equal the code table of the frozen
preregistration, so the probe that runs is the probe that was registered.

Exit codes: 0 filled, 2 an input is missing or inconsistent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness.sparse_indexer_k1_budget_v2 import PROBE_GPU_HOURS  # noqa: E402
from scripts import preregister  # noqa: E402

TEMPLATE = (
    PROJECT_ROOT
    / "experiments"
    / "manifests"
    / "q3-k1-throughput-probe-v1"
    / "q3-k1-throughput-probe.yaml"
)
EXPERIMENT_ID = "q3-k1-throughput-probe-v1"
SELF_PATH = "scripts/fill_sparse_indexer_k1_probe_manifest.py"
IDENTITY_ROW_RE = re.compile(r"^\| ([A-Za-z0-9_./-]+\.(?:py|yaml)) \| ([0-9a-f]{64}) \|$", re.M)
IMAGE_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class FillError(ValueError):
    """An input needed to fill the manifest is missing or inconsistent."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


PROBE_GPUS = 1
PROBE_MINUTES = 9  # 1 GPU x 9 minutes = PROBE_GPU_HOURS; the probe's LIMIT_S is 540 s


def _git_show(repo_root: Path, revision: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{revision}:{path}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise FillError(f"{path} is not present at image commit {revision}")
    return completed.stdout


def check_resources(manifest: dict) -> None:
    """Refuse a manifest whose GPU count, limit or cap differs from the registered probe."""
    resources = manifest.get("resources") or {}
    budget = manifest.get("budget") or {}
    if resources.get("gpus") != PROBE_GPUS:
        raise FillError(f"probe manifest must request exactly {PROBE_GPUS} GPU")
    if resources.get("minutes") != PROBE_MINUTES:
        raise FillError(f"probe manifest limit must be {PROBE_MINUTES} minutes")
    if budget.get("max_gpu_hours") != PROBE_GPU_HOURS:
        raise FillError(f"probe manifest cap must be {PROBE_GPU_HOURS} GPU-h (D20, D22)")
    if abs(PROBE_GPUS * PROBE_MINUTES / 60 - PROBE_GPU_HOURS) > 1e-9:
        raise FillError("registered probe GPU count, limit and cap are inconsistent")


def check_image_commit(repo_root: Path, git_sha: str, row: dict, table: dict) -> None:
    """Refuse an image built from a commit without the frozen row or the tabled code."""
    ledger = _git_show(repo_root, git_sha, "program/preregistrations/ledger.jsonl").decode()
    if str(row["hash"]) not in ledger:
        raise FillError("image commit does not contain the probe's frozen ledger row")
    for path, digest in table.items():
        if hashlib.sha256(_git_show(repo_root, git_sha, path)).hexdigest() != digest:
            raise FillError(f"{path} at image commit is not the tabled code")


def fill(image_receipt: Path, repo_root: Path, template: Path, output: Path) -> Path:
    receipt = json.loads(image_receipt.read_text(encoding="utf-8"))
    values = {
        "FILL-probe-image-id": receipt["image_id"],
        "FILL-probe-image-git-sha": receipt["git_sha"],
        "FILL-probe-image-source-tar-sha256": receipt["source_tar_sha256"],
    }
    if not IMAGE_RE.fullmatch(values["FILL-probe-image-id"]):
        raise FillError("image receipt image_id is not a local sha256 image id")
    if not GIT_RE.fullmatch(values["FILL-probe-image-git-sha"]):
        raise FillError("image receipt git_sha is not 40 hex")
    if not SHA_RE.fullmatch(values["FILL-probe-image-source-tar-sha256"]):
        raise FillError("image receipt source_tar_sha256 is not 64 hex")
    row = preregister.verify(
        EXPERIMENT_ID,
        ledger=repo_root / "program" / "preregistrations" / "ledger.jsonl",
        root=repo_root,
    )
    values["FILL-preregistration-sha256"] = str(row["sha256"])
    table = dict(
        IDENTITY_ROW_RE.findall((repo_root / str(row["path"])).read_text(encoding="utf-8"))
    )
    if SELF_PATH not in table:
        raise FillError("the frozen probe preregistration lacks its code digest table")
    for path, digest in table.items():
        if _sha256(PROJECT_ROOT / path) != digest:
            raise FillError(f"{path} is not the code tabled in the frozen probe preregistration")
    text = template.read_text(encoding="utf-8")
    for key, value in sorted(values.items(), key=lambda item: -len(item[0])):
        text = text.replace(f'"{key}"', f'"{value}"').replace(key, value)
    remaining = sorted(set(re.findall(r"FILL-[a-z0-9-]+", text)))
    if remaining:
        raise FillError(f"unfilled values remain: {remaining}")
    check_resources(yaml.safe_load(text))
    check_image_commit(repo_root, values["FILL-probe-image-git-sha"], row, table)
    output.mkdir(parents=True, exist_ok=True)
    target = output / template.name
    if target.exists() and target.read_text(encoding="utf-8") != text:
        raise FillError(f"{target} exists with different content; never overwrite")
    target.write_text(text, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--image-receipt", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        target = fill(args.image_receipt, args.repo_root, args.template, args.output)
    except (
        OSError,
        KeyError,
        ValueError,
        json.JSONDecodeError,
        preregister.PreregistrationError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"filled": str(target)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
