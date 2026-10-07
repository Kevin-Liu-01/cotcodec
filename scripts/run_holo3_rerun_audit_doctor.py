#!/usr/bin/env python3
"""CPU doctor for the Holo3 rerun audit (Q2 Stage 0c follow-up).

Rebuilds, from small byte-range reads of pinned public archives, the per-task
score matrices behind the two Holo3-35B-A3B rows of the OSWorld-Verified
leaderboard (maintainer run1 + repair, run2), three unlisted H Company runs and
six OpenCUA three-run sets. It checks every member against its zip CRC-32 and
the package SHA256SUMS, re-checks the leaderboard cells it cites against the
pinned sheet, reproduces the v1 analysis, and writes a receipt JSON that holds
input hashes and no infrastructure identifiers.

Stages:

* ``v1`` (default): the v1 analysis, labelled POST-HOC, plus the review's
  corrections and the EXPLORATORY OpenCUA reference. No new confirmatory data.
* ``v2-design``: design inputs for the v2 registration from already-inspected
  data only (v1 totals and URL strata, the H Company runs' rewards and
  ``actions.json``): exact power of rule (d), bootstrap power of rule (a), and
  rule (b)'s H rerun reference. It never classifies an evaluator and never
  reads the tarball.
* ``v2``: refuses to run unless ``q2-holo3-rerun-audit-v2`` is frozen in the
  repository ledger (``program/preregistrations/ledger.jsonl``, whatever
  ``--ledger`` names), and refuses ``--skip-opencua`` (a registered positive
  control). Runs rule (d) and, given a trajectory feature file, rules (a)-(c).
* ``v2-tarball``: refuses unless v2 is frozen in the repository ledger and
  ``--allow-large-download`` is given. Checks the tarball member against the
  registered size, CRC-32 and SHA-256 before any byte is fetched, downloads it
  to ``--tarball-dir``, verifies it again (an existing file is re-verified),
  scans it once and writes a feature file (trajectory ids and derived numbers
  only).

A v2 or v2-tarball receipt is labelled CONFIRMATORY only if it ran against the
repository ledger, committed and unmodified, with the code files unchanged
since the ledger's ``git_head_at_freeze``, and (when it uses trajectories)
within 14 days of the freeze. A v2 run with a feature file is CONFIRMATORY only
if ``--tarball-receipt`` names the CONFIRMATORY v2-tarball receipt that wrote
that file with the same code and freeze. Otherwise it is labelled
NON-CONFIRMATORY and names the failed checks.

Exit codes: 0 PASS, 1 a control or check failed, 2 infrastructure or integrity
error (fetch, identity, CRC-32, SHA-256 or truncated transfer), 3 refused by a
gate.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import http.client
import io
import itertools
import json
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import holo3_rerun_audit as audit  # noqa: E402
from harness import holo3_v2 as v2  # noqa: E402
from harness import osworld_source, remote_zip  # noqa: E402
from scripts import preregister  # noqa: E402

DOCTOR_NAME = "holo3-rerun-audit"
V1_EXPERIMENT_ID = "q2-holo3-rerun-audit-v1-posthoc"
V1_PREREG = "program/preregistrations/q2-holo3-rerun-audit-v1-posthoc.md"
V2_PREREG = "program/preregistrations/q2-holo3-rerun-audit-v2.md"
CODE_FILES = (
    "scripts/run_holo3_rerun_audit_doctor.py",
    "harness/holo3_rerun_audit.py",
    "harness/holo3_v2.py",
    "harness/remote_zip.py",
    "harness/osworld_source.py",
)
REPOSITORY_LEDGER = preregister.DEFAULT_LEDGER
EVIDENCE_GRADE = {
    "v1": (
        "POST-HOC REPRODUCTION: the v1 analysis was registered after the per-task files were on "
        "disk and its deciding test was nearly fixed by known totals. These numbers reproduce it "
        "with independent code; they are not confirmatory. The OpenCUA reference is EXPLORATORY."
    ),
    "v2-design": (
        "DESIGN INPUTS from already-inspected data only (v1 totals and URL strata, H Company "
        "rewards and actions.json). No evaluator is classified and no tarball byte is read."
    ),
    "v2": (
        "v2 CONFIRMATORY for rules (a)-(d) only, read against the frozen v2 registration; the "
        "external OpenCUA reference stays EXPLORATORY."
    ),
    "v2-nonconfirmatory": (
        "v2 NON-CONFIRMATORY: a registered run condition failed (see confirmatory_checks); "
        "these numbers are not the registered v2 result."
    ),
}


class GateRefused(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("v1", "v2-design", "v2", "v2-tarball"), default="v1")
    parser.add_argument(
        "--cache-dir", type=Path, default=PROJECT_ROOT / "data" / "cache" / "holo3-rerun-audit"
    )
    parser.add_argument("--max-workers", type=int, default=remote_zip.MAX_CONCURRENCY)
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[42, 43, 44],
        help="first seed is v1's registered seed; the others are Monte Carlo sensitivity",
    )
    parser.add_argument("--sign-flip-draws", type=int, default=1_000_000)
    parser.add_argument("--model-draws", type=int, default=100_000)
    parser.add_argument("--power-sims-a", type=int, default=400, help="v2 design: rule (a)")
    parser.add_argument("--skip-opencua", action="store_true", help="v1 only; v2 refuses it")
    parser.add_argument(
        "--h-steps", action="store_true", help="v1: also read H runs' actions.json (step summary)"
    )
    parser.add_argument("--matrix-output", type=Path, help="write the Holo3 per-task CSV here")
    parser.add_argument("--ledger", type=Path, default=preregister.DEFAULT_LEDGER)
    parser.add_argument("--trajectory-features", type=Path, help="v2: feature file from v2-tarball")
    parser.add_argument(
        "--tarball-receipt",
        type=Path,
        help="v2: the v2-tarball receipt that wrote --trajectory-features (provenance check)",
    )
    parser.add_argument("--tarball-dir", type=Path, help="v2-tarball: host scratch directory")
    parser.add_argument("--allow-large-download", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.max_workers <= remote_zip.MAX_CONCURRENCY:
        parser.error(f"--max-workers must be 1..{remote_zip.MAX_CONCURRENCY}")
    if args.seeds[0] != 42:
        parser.error("the first seed must be 42, v1's registered seed")
    for path in (args.output, args.matrix_output):
        if path is not None and path.exists():
            parser.error(f"refusing to overwrite {path}")
    return args


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #


def code_file_hashes() -> dict[str, str]:
    return {
        rel: hashlib.sha256((PROJECT_ROOT / rel).read_bytes()).hexdigest() for rel in CODE_FILES
    }


def code_hashes() -> dict[str, Any]:
    files = code_file_hashes()
    head = dirty = None
    try:
        head = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(PROJECT_ROOT), "status", "--porcelain", "--", *CODE_FILES],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        pass
    return {"files_sha256": files, "git_head": head, "code_files_dirty": dirty}


def prereg_state(experiment_id: str, rel: str, ledger: Path) -> dict[str, Any]:
    path = PROJECT_ROOT / rel
    state: dict[str, Any] = {
        "experiment_id": experiment_id,
        "path": rel,
        "file_sha256": preregister.sha256_file(path) if path.is_file() else None,
    }
    try:
        row = preregister.verify(experiment_id, ledger=ledger, root=PROJECT_ROOT)
    except preregister.PreregistrationError as exc:
        state["ledger"] = {"frozen": False, "reason": str(exc)}
    else:
        state["ledger"] = {
            "frozen": True,
            "sha256": row["sha256"],
            "row_hash": row["hash"],
            "frozen_at": row["frozen_at"],
            "git_head_at_freeze": row.get("git_head_at_freeze"),
        }
    return state


def _git_ok(*command: str) -> bool:
    try:
        completed = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), *command], capture_output=True, check=False
        )
    except OSError:
        return False
    return completed.returncode == 0


def features_from_confirmatory_scan(
    features: Path, tarball_receipt: Path | None, ledger_state: dict[str, Any]
) -> bool:
    """True only if ``tarball_receipt`` is the CONFIRMATORY v2-tarball receipt that
    wrote ``features``, from the registered tarball, with this code and this freeze."""
    if tarball_receipt is None:
        return False
    try:
        scan = json.loads(tarball_receipt.read_text())
        checks = scan["confirmatory_checks"]
        row_hash = ledger_state.get("row_hash")
        return bool(
            scan["doctor"] == DOCTOR_NAME
            and scan["stage"] == "v2-tarball"
            and scan["status"] == "PASS"
            and scan["label"] == "v2 CONFIRMATORY"
            and checks
            and all(checks.values())
            and scan["code"]["files_sha256"] == code_file_hashes()
            and row_hash
            and scan["preregistrations"]["v2"]["ledger"]["row_hash"] == row_hash
            and scan["results"]["tarball"]["sha256"] == v2.TARBALL_SHA256
            and scan["results"]["tarball_scan"]["feature_file_sha256"]
            == hashlib.sha256(features.read_bytes()).hexdigest()
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def confirmatory_checks(
    args: argparse.Namespace, v2_state: dict[str, Any], *, uses_trajectories: bool
) -> dict[str, bool]:
    """Run conditions the v2 registration names; any False makes the run NON-CONFIRMATORY."""
    ledger = v2_state.get("ledger", {})
    repository = args.ledger.resolve() == REPOSITORY_LEDGER.resolve()
    try:
        rel = REPOSITORY_LEDGER.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        rel = None
    head = ledger.get("git_head_at_freeze")
    checks = {
        "repository_ledger": repository,
        "ledger_committed_and_unmodified": repository
        and rel is not None
        and _git_ok("ls-files", "--error-unmatch", "--", rel)
        and _git_ok("diff", "--quiet", "HEAD", "--", rel),
        "code_unchanged_since_freeze": bool(head)
        and _git_ok("diff", "--quiet", str(head), "--", *CODE_FILES),
    }
    if uses_trajectories:
        frozen_at = ledger.get("frozen_at")
        checks["within_14_days_of_freeze"] = bool(frozen_at) and (
            datetime.now(UTC) - datetime.fromisoformat(str(frozen_at))
            <= timedelta(days=v2.FINAL_WINDOW_DAYS)
        )
    features = getattr(args, "trajectory_features", None)
    if getattr(args, "stage", None) == "v2" and features is not None:
        checks["trajectory_features_from_confirmatory_scan"] = features_from_confirmatory_scan(
            features, getattr(args, "tarball_receipt", None), ledger
        )
    return checks


REPOSITORY_LEDGER_REL = "program/preregistrations/ledger.jsonl"


def require_repository_freeze(receipt: dict[str, Any]) -> None:
    """Freeze gate for the v2 stages.

    v2 must be frozen in the repository ledger, whatever ``--ledger`` names: a
    freeze in a scratch ledger alone must not unblind the class-outcome join
    or start the tarball download.
    """
    state = prereg_state(v2.V2_EXPERIMENT_ID, V2_PREREG, REPOSITORY_LEDGER)
    gate = {
        "repository_ledger_frozen": bool(state["ledger"]["frozen"]),
        "run_ledger_frozen": bool(receipt["preregistrations"]["v2"]["ledger"]["frozen"]),
    }
    receipt["freeze_gate"] = gate
    if not all(gate.values()):
        raise GateRefused(
            f"{v2.V2_EXPERIMENT_ID} is not frozen in the repository ledger "
            f"({REPOSITORY_LEDGER_REL}) and the ledger this run names"
        )


def make_context(args: argparse.Namespace) -> tuple[audit.FetchContext, remote_zip.TransferStats]:
    transfer = remote_zip.TransferStats()
    semaphore = threading.Semaphore(args.max_workers)

    def open_archive(spec: audit.ArchiveSpec) -> remote_zip.RangeSource:
        return remote_zip.HFRangeSource(
            audit.DATASET_REPO,
            audit.DATASET_REVISION,
            spec.path,
            expected_size=spec.size,
            expected_sha256=spec.lfs_sha256,
            stats=transfer,
            semaphore=semaphore,
        )

    cache = remote_zip.MemberCache(args.cache_dir / "members")
    return audit.FetchContext(open_archive, cache=cache, max_workers=args.max_workers), transfer


# --------------------------------------------------------------------------- #
# Shared loading
# --------------------------------------------------------------------------- #


def load_configs(
    commit: str, universe: list[tuple[str, str]], cache_dir: Path
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    files = osworld_source.GitHubCommitFiles(
        audit.OSWORLD_REPO, commit, cache_dir=cache_dir / "osworld"
    )
    configs: dict[str, dict[str, Any]] = {}
    blobs: dict[str, str] = {}
    tree = files.tree()
    for domain, task in universe:
        path = f"evaluation_examples/examples/{domain}/{task}.json"
        configs[task] = json.loads(files.read(path))
        blobs[path] = tree[path]
    info = osworld_source.describe_fetch(files)
    info["configs"] = len(configs)
    info["config_blob_manifest_sha256"] = audit._digest_manifest(blobs)
    info["license"] = audit.OSWORLD_LICENSE
    return configs, info


def load_leaderboard(cache_dir: Path) -> tuple[dict[int, dict[str, str]], dict[str, Any]]:
    data = osworld_source.fetch_pinned_file(
        audit.LEADERBOARD_URL, audit.LEADERBOARD_SHA256, cache_dir=cache_dir / "leaderboard"
    )
    rows = osworld_source.read_xlsx_first_sheet(data)
    return rows, {
        "url": audit.LEADERBOARD_URL,
        "sha256": audit.LEADERBOARD_SHA256,
        "site_commit": audit.LEADERBOARD_SITE_COMMIT,
        "license": audit.LEADERBOARD_LICENSE,
    }


def foreseeability(net: int, alpha: float = 0.05) -> int:
    """Largest discordant count at which exact McNemar with this net is < alpha."""
    best = 0
    for k in range(net, 400, 2):
        if stats.binomtest((k + net) // 2, k, 0.5).pvalue < alpha:
            best = k
    return best


def matrix_rows(m: audit.V1Matrix, h: audit.HRuns) -> list[dict[str, Any]]:
    rows = []
    for t in m.tasks:
        a, b = m.v1[t] or {}, m.v2[t] or {}
        rows.append(
            {
                "domain": m.domain_of[t],
                "task_id": t,
                "web_dependent_v1": int(m.web[t]),
                "run1_score": m.s1[t],
                "run1_source": m.v1_source[t],
                "run1_flags": "|".join(sorted(m.flags[t][0])),
                "run1_elapsed_s": a.get("elapsed_s"),
                "run1_agp_outcome": str(a.get("agp_message", "")).split(" (")[0] or None,
                "run2_score": m.s2[t],
                "run2_flags": "|".join(sorted(m.flags[t][1])),
                "run2_elapsed_s": b.get("elapsed_s"),
                "run2_agp_outcome": str(b.get("agp_message", "")).split(" (")[0] or None,
                **{f"H{tag}_reward": h.rewards[tag].get(t) for tag in audit.H_RUN_TAGS},
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    data = buffer.getvalue().encode()
    audit.assert_public_safe([list(r.values()) for r in rows], "matrix")
    _atomic_write(path, data)
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


# --------------------------------------------------------------------------- #
# Stages
# --------------------------------------------------------------------------- #


def clean_tasks(m: audit.V1Matrix) -> list[str]:
    """v1's clean set: scored in both runs, no flag other than F1 in either."""
    return [
        t
        for t in m.tasks
        if m.s1[t] is not None
        and m.s2[t] is not None
        and not ((m.flags[t][0] | m.flags[t][1]) - {"F1"})
    ]


def run_common(
    args: argparse.Namespace,
    ctx: audit.FetchContext,
    receipt: dict[str, Any],
    commit: str,
    *,
    h_features: bool = False,
):
    cases = receipt["cases"]
    rows, lb_info = load_leaderboard(args.cache_dir)
    receipt["inputs"]["leaderboard"] = lb_info
    cases["leaderboard_constants_match_pinned_sheet"] = audit.check_leaderboard_constants(rows)

    pkg = audit.load_verified_package(ctx)
    # load_verified_package raises (exit 2) on the first mismatch; this case
    # re-checks every member it returned against SHA256SUMS.
    mismatched = [rel for rel, d in pkg.member_sha256.items() if pkg.sha256sums.get(rel) != d]
    cases["verified_members_match_sha256sums"] = {
        "status": "PASS" if pkg.member_sha256 and not mismatched else "FAIL",
        "members_checked": len(pkg.member_sha256),
        "mismatched": len(mismatched),
    }
    receipt["inputs"]["verified_package"] = {
        "root": audit.VERIFIED_ROOT.rstrip("/"),
        "sha256sums_entries": len(pkg.sha256sums),
        "member_manifest_sha256": audit._digest_manifest(pkg.member_sha256),
        "members_read": len(pkg.member_sha256) + 1,
        "tarball_member": pkg.tarball,
    }
    configs, osw_info = load_configs(commit, pkg.universe, args.cache_dir)
    receipt["inputs"]["osworld_configs"] = osw_info
    web = {t: audit.web_dependent(configs[t]) for t in pkg.tasks}
    m = audit.build_v1_matrix(pkg, web)
    collected: dict[str, dict[str, v2.TrajectoryFeatures]] = collections.defaultdict(dict)

    def on_actions(tag: str, task: str, entries: Any) -> None:
        features = v2.TrajectoryFeatures(task)
        try:
            v2.parse_actions(features, entries)
        except ValueError:
            features.parsed = False
        collected[tag][task] = features

    h = audit.load_h_runs(
        ctx, pkg.universe, with_steps=h_features, on_actions=on_actions if h_features else None
    )
    h.features = dict(collected)
    receipt["inputs"]["h_runs"] = {
        "nested": h.nested,
        "member_manifest_sha256": audit._digest_manifest(h.member_sha256),
        "crc_checked_members": len(h.member_sha256),
        "note": "nested zips cannot be hashed without a full download; "
        "inner members are CRC-checked",
    }
    cases["holo3_leaderboard_domain_cells"] = audit.holo3_domain_control(m)
    cases["package_summaries_agree_with_per_task_files"] = audit.summary_control(pkg, m)
    receipt["results"]["leaderboard_rank_by_group_mean"] = audit.rank_by_group_mean(
        rows, "Holo3-35B-A3B", "100"
    )
    return pkg, m, h, configs, rows


def opencua(args: argparse.Namespace, ctx: audit.FetchContext, receipt: dict[str, Any]):
    sets = [audit.load_opencua(ctx, spec) for spec in audit.OPENCUA_ARCHIVES.values()]
    receipt["cases"]["opencua_turn_totals_match_leaderboard"] = audit.opencua_leaderboard_control(
        sets
    )
    return sets


def stage_v1(args: argparse.Namespace, ctx: audit.FetchContext, receipt: dict[str, Any]) -> None:
    pkg, m, h, _, _ = run_common(
        args, ctx, receipt, audit.OSWORLD_V1_CONFIG_COMMIT, h_features=args.h_steps
    )
    results = receipt["results"]
    main = audit.analyze_v1(
        m, h, seed=args.seeds[0], sign_flip_draws=args.sign_flip_draws, model_draws=args.model_draws
    )
    results["v1"] = {"label": "POST-HOC", **main}
    if args.sign_flip_draws == 1_000_000 and args.model_draws == 100_000:
        receipt["cases"]["v1_recorded_numbers_reproduced"] = audit.v1_reproduction_checks(main)
    results["v1_monte_carlo_seed_sensitivity"] = {}
    for seed in args.seeds[1:]:
        other = audit.analyze_v1(
            m, h, seed=seed, sign_flip_draws=args.sign_flip_draws, model_draws=args.model_draws
        )
        results["v1_monte_carlo_seed_sensitivity"][str(seed)] = {
            "sign_flip_p": {k: v["p"] for k, v in other["sign_flip"].items()},
            "h_only_model_p": other["h_only_model"]["p_abs_gap_ge_observed"],
            "verdict": other["decision"]["verdict"],
        }
    net_c = main["mcnemar"]["ge"]["C"]["a_only"] - main["mcnemar"]["ge"]["C"]["b_only"]
    net_clean = main["mcnemar"]["ge"]["clean"]["a_only"] - main["mcnemar"]["ge"]["clean"]["b_only"]
    results["v1_foreseeability"] = {
        "net_common": net_c,
        "max_discordant_with_p_below_0.05_common": foreseeability(net_c),
        "net_clean": net_clean,
        "max_discordant_with_p_below_0.05_clean": foreseeability(net_clean),
        "note": "with the net fixed by known totals, R3 fires for any discordance "
        "up to these counts",
    }
    results["five_run_comparison"] = {
        "label": "EXPLORATORY (review E3)",
        **audit.five_run_comparison(m, h),
    }
    results["power"] = audit.power_summary(main["reference_noise"]["q_h"])
    if not args.skip_opencua:
        sets = opencua(args, ctx, receipt)
        holo3_z = main["mcnemar"]["ge"]["C"]["z"]
        results["external_reference"] = audit.opencua_reference(sets, holo3_z, main["h_pairs"])
    if args.matrix_output:
        receipt["outputs"] = {
            "holo3_matrix_csv_sha256": write_csv(args.matrix_output, matrix_rows(m, h)),
            "holo3_matrix_rows": len(m.tasks),
        }


def rule_b_design(h: audit.HRuns, clean: list[str], n_run2_unique: int) -> dict[str, Any]:
    """Rule (b)'s H rerun reference and its behaviour on exchangeable reruns.

    The H runs are already inspected and are not v2's confirmatory data. Their
    screenshots are not read, so only the tool-error and text criteria apply.
    """
    features = h.features
    for runs in features.values():
        for item in runs.values():
            item.identical_run = 0  # screenshots not read
    rewards = {tag: h.rewards[tag] for tag in audit.H_RUN_TAGS}
    out: dict[str, Any] = {"note": "tool-error and text criteria only; no screenshots read"}
    calibration: dict[str, Any] = {}
    for tag in audit.H_RUN_TAGS:
        groups: dict[str, list[v2.TrajectoryFeatures]] = {"pass": [], "fail": []}
        for task, item in features.get(tag, {}).items():
            if task in rewards[tag]:
                groups["pass" if rewards[tag][task] >= 0.5 else "fail"].append(item)
        calibration[tag] = {
            outcome: {
                "n": len(items),
                "env_text_any": sum(1 for f in items if f.env_text_hits),
                "tool_error_any": sum(1 for f in items if f.tool_error_entries),
                "step_cap": sum(1 for f in items if f.steps >= v2.STEP_CAP),
                "env_text_and_step_cap": sum(
                    1 for f in items if f.env_text_hits and f.steps >= v2.STEP_CAP
                ),
                "final_tool_answer": sum(1 for f in items if f.final_tool == "answer"),
                "pattern_trajectories": dict(
                    sorted(collections.Counter(k for f in items for k in f.env_text_hits).items())
                ),
            }
            for outcome, items in groups.items()
        }
    out["signature_rates_all_tasks"] = calibration
    passing_clean = [
        f
        for tag in audit.H_RUN_TAGS
        for t, f in features.get(tag, {}).items()
        if t in clean and rewards[tag].get(t) is not None and rewards[tag][t] >= 0.5
    ]
    out["specificity_on_h_passing_clean_episodes"] = {
        "episodes": len(passing_clean),
        "share_firing": {
            name: (
                sum(1 for f in passing_clean if v2.env_criteria(f)[name]) / len(passing_clean)
                if passing_clean
                else None
            )
            for name in v2.PRIMARY_ENV_CRITERIA
        },
    }
    primary = v2.h_reference(features, rewards, clean)
    cap_first = v2.h_reference(features, rewards, clean, step_cap_first=True)
    out["reference_primary"] = primary
    out["reference_step_cap_first"] = cap_first
    out["run2_unique_failures"] = n_run2_unique
    out["label_thresholds_for_run2"] = {
        "primary": v2.rule_b_thresholds(n_run2_unique, primary["pooled"]),
        "step_cap_first": v2.rule_b_thresholds(n_run2_unique, cap_first["pooled"]),
    }
    null_check = {}
    for order, ref in (("primary", primary), ("step_cap_first", cap_first)):
        rows = {}
        for tag in audit.H_RUN_TAGS:
            run = ref["per_run"][tag]
            others = v2.pooled(ref["per_run"][o] for o in audit.H_RUN_TAGS if o != tag)
            share_only = (
                "R1-retro: infrastructure"
                if run["tasks"] and run["environment"] / run["tasks"] >= v2.SHARE_BAR
                else "agent-side session variation"
                if run["tasks"] and run["agent_side"] / run["tasks"] >= v2.SHARE_BAR
                else "unexplained"
            )
            rows[tag] = {
                **v2.rule_b_label(run, others),
                "superseded_share_only_verdict": share_only,
            }
        null_check[order] = rows
    out["null_check_each_h_run_vs_other_two"] = null_check
    return out


def stage_v2_design(
    args: argparse.Namespace, ctx: audit.FetchContext, receipt: dict[str, Any]
) -> None:
    """Design inputs for v2 from already-inspected data. Classifies no evaluator."""
    pkg, m, h, _, _ = run_common(
        args, ctx, receipt, audit.OSWORLD_V1_CONFIG_COMMIT, h_features=True
    )
    clean = clean_tasks(m)
    s1 = {t: float(m.s1[t]) for t in clean}  # type: ignore[arg-type]
    s2 = {t: float(m.s2[t]) for t in clean}  # type: ignore[arg-type]
    strata = {}
    for name in v2.STRATA:
        tasks = [t for t in clean if m.web[t] == (name == "web")]
        strata[name] = {
            "tasks": len(tasks),
            "run1_only": sum(1 for t in tasks if s1[t] >= 0.5 > s2[t]),
            "run2_only": sum(1 for t in tasks if s2[t] >= 0.5 > s1[t]),
        }
    net_all = sum(v["run1_only"] - v["run2_only"] for v in strata.values())
    h_rewards = {tag: h.rewards[tag] for tag in audit.H_RUN_TAGS}
    run2_unique = v2.unique_failures(s2, s1, h_rewards, clean)
    run1_unique = v2.unique_failures(s1, s2, h_rewards, clean)
    results = receipt["results"]
    design: dict[str, Any] = {
        "label": "v2 design inputs from already-inspected data (v1 totals and URL strata, H runs)",
        "clean_tasks": len(clean),
        "url_strata_known_before_registration": strata,
        "net_flips_all": net_all,
        "rule_d_share_bound": {
            "max_share_from_web_stratum": (
                strata["web"]["run1_only"] / net_all if net_all else None
            ),
            "note": "an L set inside the web stratum can carry at most the web stratum's "
            "run1-only tasks",
        },
        "rule_d_power_exact": v2.power_rule_d(strata),
        "unique_failures": {"run2": len(run2_unique), "run1": len(run1_unique)},
    }
    # Rule (a)'s own step definition (entries that are objects with an
    # ``action`` key), applied to the H trajectories.
    h_steps = {
        tag: {t: f.steps for t, f in h.features.get(tag, {}).items() if f.parsed}
        for tag in audit.H_RUN_TAGS
    }
    pairs: list[tuple[int, int]] = []
    baseline = []
    for a_tag, b_tag in itertools.combinations(audit.H_RUN_TAGS, 2):
        a, b = h_steps[a_tag], h_steps[b_tag]
        common = sorted(set(a) & set(b))
        pairs += [(a[t], b[t]) for t in common]
        x = [a[t] for t in common]
        y = [b[t] for t in common]
        shift = v2.step_shift(np.asarray(x, float), np.asarray(y, float))
        baseline.append({"pair": [a_tag, b_tag], "n": len(common), **shift})
    design["h_step_baseline"] = baseline
    design["rule_a_power"] = v2.power_rule_a(
        pairs, n=len(clean), sims=args.power_sims_a, seeds=args.seeds
    )
    # Power given the clean set's known outcome pattern (pre-freeze audit):
    # run1-only and run2-only tasks pair a passing with a failing episode.
    counts = {
        "both_pass": sum(1 for t in clean if s1[t] >= 0.5 and s2[t] >= 0.5),
        "both_fail": sum(1 for t in clean if s1[t] < 0.5 and s2[t] < 0.5),
        "run1_only": sum(1 for t in clean if s1[t] >= 0.5 > s2[t]),
        "run2_only": sum(1 for t in clean if s2[t] >= 0.5 > s1[t]),
    }
    pools = v2.outcome_pools(h_steps, h_rewards)
    design["clean_outcome_counts"] = counts
    design["rule_a_outcome_pools"] = {
        c: {
            "pairs": len(v),
            "step_cap_share_of_second": (
                sum(1 for _, b in v if b >= v2.STEP_CAP) / len(v) if v else None
            ),
        }
        for c, v in pools.items()
    }
    design["rule_a_power_by_outcome"] = v2.power_rule_a_by_outcome(
        pools, counts, sims=args.power_sims_a, seeds=args.seeds
    )
    design["rule_d_size_all_allocations"] = v2.size_rule_d_all_allocations(strata)
    design["rule_b"] = rule_b_design(h, clean, len(run2_unique))
    design["rule_b_power"] = {
        "assumption": "each of the run2-unique failures falls in the class independently "
        "with the given share; full coverage; for agent-side, no environment failures",
        "rows": v2.power_rule_b(
            len(run2_unique),
            design["rule_b"]["label_thresholds_for_run2"]["primary"],
            reference=design["rule_b"]["reference_primary"]["pooled"],
        ),
    }
    receipt["cases"]["rule_b_h_reference_matches_registration"] = h_reference_control(
        design["rule_b"]["reference_primary"]["pooled"]
    )
    results["v2_design"] = design


def h_reference_control(observed: dict[str, Any]) -> dict[str, Any]:
    """The pooled H rerun reference must equal the numbers registered in the v2 draft."""
    registered = v2.REGISTERED_H_REFERENCE
    got = {key: observed[key] for key in ("tasks", "environment", "agent_side", "classes")}
    if registered is None:
        return {"status": "FAIL", "detail": "no registered H reference"}
    return {"status": "PASS" if got == registered else "FAIL", "got": got, "registered": registered}


def stage_v2(args: argparse.Namespace, ctx: audit.FetchContext, receipt: dict[str, Any]) -> None:
    require_repository_freeze(receipt)
    if args.skip_opencua:
        raise GateRefused("--skip-opencua drops a positive control the v2 registration requires")
    pkg, m, h, configs, _ = run_common(
        args, ctx, receipt, audit.OSWORLD_V2_CONFIG_COMMIT, h_features=True
    )
    manifest = receipt["inputs"]["osworld_configs"].get("config_blob_manifest_sha256")
    receipt["cases"]["v2_config_blobs_equal_v1"] = {
        "status": "PASS" if manifest == v2.V1_CONFIG_BLOB_MANIFEST else "FAIL",
        "got": manifest,
        "registered": v2.V1_CONFIG_BLOB_MANIFEST,
    }
    s1 = {t: v for t, v in m.s1.items() if v is not None}
    s2 = {t: v for t, v in m.s2.items() if v is not None}
    common = [t for t in m.tasks if t in s1 and t in s2]
    clean = clean_tasks(m)
    h_rewards = {tag: h.rewards[tag] for tag in audit.H_RUN_TAGS}
    for runs in h.features.values():
        for item in runs.values():
            item.identical_run = 0  # H screenshots are not read
    receipt["cases"]["rule_b_h_reference_matches_registration"] = h_reference_control(
        v2.h_reference(h.features, h_rewards, clean)["pooled"]
    )
    classes = {t: v2.classify_evaluator(configs[t]) for t in m.tasks}
    labels = {t: c.label for t, c in classes.items()}
    narrow = {t: ("L" if c.narrow_l else "not L") for t, c in classes.items()}
    results = receipt["results"]
    results["evaluator_classes"] = {
        "counts_all": dict(sorted(collections.Counter(labels.values()).items())),
        "narrow_L_count_all": sum(1 for c in classes.values() if c.narrow_l),
        "per_task": {
            t: {"class": c.label, "narrow_L": c.narrow_l, "reasons": list(c.reasons)}
            for t, c in classes.items()
        },
    }
    d = v2.rule_d(labels, s1, s2, clean, m.web)
    d_narrow = v2.rule_d(narrow, s1, s2, clean, m.web)
    abc = None
    if args.trajectory_features:
        payload = json.loads(args.trajectory_features.read_text())
        features = {
            key: v2.TrajectoryFeatures.from_public(item)
            for key, item in payload["features"].items()
        }

        def run_abc(keep: set[str], tasks: list[str]) -> dict[str, Any]:
            return v2.rules_abc(
                features=features,
                status1=m.v1,
                status2=m.v2,
                s1={t: v for t, v in s1.items() if t in keep},
                s2={t: v for t, v in s2.items() if t in keep},
                clean=tasks,
                h_rewards=h_rewards,
                h_features=h.features,
            )

        abc = run_abc(set(s1) | set(s2), clean)
        receipt["inputs"]["trajectory_features_sha256"] = hashlib.sha256(
            args.trajectory_features.read_bytes()
        ).hexdigest()
        if args.tarball_receipt is not None:
            receipt["inputs"]["tarball_receipt_sha256"] = hashlib.sha256(
                args.tarball_receipt.read_bytes()
            ).hexdigest()
        # Registered sensitivity: drop every clean task whose run1 or run2
        # trajectory lies in the tarball region read before registration.
        probed = {
            k
            for k, f in features.items()
            if f.compressed_offset is None or f.compressed_offset < v2.PROBE_BYTES
        }
        unprobed = [
            t
            for t in clean
            if str((m.v1[t] or {}).get("trajectory_id")) not in probed
            and str((m.v2[t] or {}).get("trajectory_id")) not in probed
        ]
        keep = set(unprobed) | ((set(s1) | set(s2)) - set(clean))
        probe_abc = run_abc(keep, unprobed)
        main_decisions = v2.v2_decisions(d, abc, rule_d_narrow=d_narrow)
        probe_decisions = v2.v2_decisions(d, probe_abc, rule_d_narrow=d_narrow)
        results["v2_probe_sensitivity"] = {
            "label": "registered sensitivity: tasks whose trajectories were in the probed region "
            "are excluded",
            "probe_bytes": v2.PROBE_BYTES,
            "trajectories_in_probed_region": len(probed),
            "clean_tasks_kept": len(unprobed),
            "rules_abc": probe_abc,
            "decisions": probe_decisions,
            "robust": {
                rule: main_decisions[rule] == probe_decisions[rule]
                for rule in ("rule_a", "rule_b", "rule_c")
            },
        }
    results["v2"] = {
        "label": "CONFIRMATORY (v2 rules a-d)",
        "rule_d": d,
        "rule_d_narrow_L_sensitivity": d_narrow,
        "rules_abc": abc,
        "decisions": v2.v2_decisions(d, abc, rule_d_narrow=d_narrow),
    }
    sets = opencua(args, ctx, receipt)
    main_z = audit.mcnemar(common, s1, s2).z
    h_pairs = []
    for a_tag, b_tag in itertools.combinations(audit.H_RUN_TAGS, 2):
        a, b = h.rewards[a_tag], h.rewards[b_tag]
        ts = [t for t in m.tasks if t in a and t in b]
        h_pairs.append(audit.mcnemar(ts, a, b).as_dict())
    results["external_reference"] = audit.opencua_reference(sets, main_z, h_pairs)


def stage_v2_tarball(
    args: argparse.Namespace, ctx: audit.FetchContext, receipt: dict[str, Any]
) -> None:
    require_repository_freeze(receipt)
    if not args.allow_large_download or args.tarball_dir is None:
        raise GateRefused("v2-tarball needs --allow-large-download and --tarball-dir")
    pkg = audit.load_verified_package(ctx)
    source = ctx.source(audit.VERIFIED_ARCHIVE)
    (member,) = remote_zip.select(
        ctx.listing(audit.VERIFIED_ARCHIVE), [audit.VERIFIED_ROOT + audit.TARBALL_RELPATH]
    )
    # Section 1's literals, checked before any tarball byte is fetched.
    differs = [
        name
        for name, ok in (
            ("size", member.file_size == v2.TARBALL_SIZE),
            ("crc32", member.crc == v2.TARBALL_CRC32),
            ("sha256", pkg.tarball["sha256_from_sha256sums"] == v2.TARBALL_SHA256),
        )
        if not ok
    ]
    if differs:
        raise remote_zip.ZipIntegrityError(
            f"tarball member differs from the registered literals: {differs}"
        )
    dest = args.tarball_dir / "trajectories.tar.gz"
    receipt["results"]["tarball"] = v2.download_stored_member(
        source, member, dest, expected_sha256=v2.TARBALL_SHA256
    )
    layout: dict[str, int] = {}
    features = v2.scan_trajectory_tarball(dest, layout=layout)
    wanted = {
        str(record.get("trajectory_id"))
        for run in ("run1", "repair", "run2")
        for record in pkg.status[run].values()
        if record.get("trajectory_id")
    }
    public = {k: f.public() for k, f in sorted(features.items()) if k in wanted}
    scan: dict[str, Any] = {
        "trajectories_in_tarball": len(features),
        "trajectories_matching_status_files": len(public),
        "status_trajectory_ids": len(wanted),
        "layout": layout,
    }
    receipt["results"]["tarball_scan"] = scan
    try:
        audit.assert_public_safe(public, "trajectory features")
    except audit.PublicSafetyError:
        receipt["cases"]["feature_file_public_safety"] = {
            "status": "FAIL",
            "detail": "feature file withheld: a value matched a public-safety pattern",
        }
        return
    receipt["cases"]["feature_file_public_safety"] = {"status": "PASS"}
    out = args.tarball_dir / "trajectory_features.json"
    _atomic_write(out, json.dumps({"features": public}, sort_keys=True).encode())
    scan["feature_file_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def overall_status(cases: dict[str, Any]) -> str:
    return "PASS" if all(c.get("status") == "PASS" for c in cases.values()) else "FAIL"


STAGES = {
    "v1": stage_v1,
    "v2-design": stage_v2_design,
    "v2": stage_v2,
    "v2-tarball": stage_v2_tarball,
}


def main(argv: list[str] | None = None, *, context_factory=make_context) -> int:
    args = parse_args(argv)
    started = time.time()
    ctx, transfer = context_factory(args)
    preregs = {
        "v1_posthoc": prereg_state(V1_EXPERIMENT_ID, V1_PREREG, args.ledger),
        "v2": prereg_state(v2.V2_EXPERIMENT_ID, V2_PREREG, args.ledger),
    }
    grade_key = args.stage if args.stage in ("v1", "v2-design") else "v2"
    label = {"v1": "POST-HOC", "v2-design": "DESIGN"}.get(args.stage, "v2 CONFIRMATORY")
    checks: dict[str, bool] | None = None
    if args.stage in ("v2", "v2-tarball"):
        confirmatory = preregs["v2"]["ledger"]["frozen"] and not (
            args.stage == "v2" and args.skip_opencua
        )
        if preregs["v2"]["ledger"]["frozen"]:
            checks = confirmatory_checks(
                args,
                preregs["v2"],
                uses_trajectories=args.stage == "v2-tarball"
                or args.trajectory_features is not None,
            )
            confirmatory = confirmatory and all(checks.values())
        if not confirmatory:
            grade_key, label = "v2-nonconfirmatory", "v2 NON-CONFIRMATORY"
    receipt: dict[str, Any] = {
        "doctor": DOCTOR_NAME,
        "stage": args.stage,
        "label": label,
        "evidence_grade": EVIDENCE_GRADE[grade_key],
        "started_at": datetime.now(UTC).isoformat(),
        "code": code_hashes(),
        "preregistrations": preregs,
        "ledger": {
            "is_repository_ledger": args.ledger.resolve() == REPOSITORY_LEDGER.resolve(),
            "sha256": preregister.sha256_file(args.ledger) if args.ledger.is_file() else None,
        },
        "parameters": {
            "seeds": args.seeds,
            "sign_flip_draws": args.sign_flip_draws,
            "model_draws": args.model_draws,
            "power_sims_rule_a": args.power_sims_a,
            "max_workers": args.max_workers,
            "h_steps": args.h_steps,
            "opencua": not args.skip_opencua,
            "trajectory_features": args.trajectory_features is not None,
            "tarball_receipt": args.tarball_receipt is not None,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "inputs": {
            "dataset": {
                "repo": audit.DATASET_REPO,
                "revision": audit.DATASET_REVISION,
                "license": audit.DATASET_LICENSE,
            }
        },
        "cases": {},
        "results": {},
    }
    if checks is not None:
        receipt["confirmatory_checks"] = checks
    code = 0
    try:
        STAGES[args.stage](args, ctx, receipt)
        receipt["status"] = overall_status(receipt["cases"]) if receipt["cases"] else "PASS"
        code = 0 if receipt["status"] == "PASS" else 1
    except GateRefused as exc:
        receipt["status"] = "REFUSED"
        receipt["error"] = audit.scrub(str(exc))
        code = 3
    except (
        remote_zip.RemoteZipError,
        osworld_source.SourceFetchError,
        http.client.HTTPException,
        ValueError,
        KeyError,
        OSError,
    ) as exc:
        receipt["status"] = "INFRA_ERROR"
        receipt["error"] = {"type": type(exc).__name__, "message": audit.scrub(str(exc))[:500]}
        code = 2
    receipt["inputs"]["archives"] = ctx.identities()
    receipt["transfer"] = {**transfer.as_dict(), "members_read": ctx.members_read}
    receipt["elapsed_seconds"] = round(time.time() - started, 3)
    try:
        audit.assert_public_safe(receipt)
        receipt["cases"]["receipt_public_safety"] = {"status": "PASS"}
    except audit.PublicSafetyError as exc:
        receipt = {
            "doctor": DOCTOR_NAME,
            "stage": args.stage,
            "status": "FAIL",
            "cases": {"receipt_public_safety": {"status": "FAIL", "detail": str(exc)}},
        }
        code = 1
    _atomic_write(args.output, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps({"status": receipt["status"], "output": str(args.output)}, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
