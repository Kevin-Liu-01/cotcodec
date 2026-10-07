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
* ``v2``: refuses to run unless ``q2-holo3-rerun-audit-v2`` is frozen in the
  preregistration ledger. Runs rule (d) and, given a trajectory feature file,
  rules (a)-(c).
* ``v2-tarball``: refuses unless v2 is frozen and ``--allow-large-download`` is
  given. Downloads the 5.75 GB trajectory tarball to ``--tarball-dir``,
  verifies size, CRC-32 and SHA-256, scans it once and writes a feature file
  (trajectory ids and derived numbers only).

Exit codes: 0 PASS, 1 a control or check failed, 2 infrastructure or integrity
error, 3 refused by a gate.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import itertools
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
EVIDENCE_GRADE = {
    "v1": (
        "POST-HOC REPRODUCTION: the v1 analysis was registered after the per-task files were on "
        "disk and its deciding test was nearly fixed by known totals. These numbers reproduce it "
        "with independent code; they are not confirmatory. The OpenCUA reference is EXPLORATORY."
    ),
    "v2": (
        "v2 CONFIRMATORY for rules (a)-(d) only, read against the frozen v2 registration; the "
        "external OpenCUA reference stays EXPLORATORY."
    ),
}


class GateRefused(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("v1", "v2", "v2-tarball"), default="v1")
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
    parser.add_argument("--power-sims-d", type=int, default=2000, help="v2 design: rule (d)")
    parser.add_argument("--power-sims-a", type=int, default=400, help="v2 design: rule (a)")
    parser.add_argument("--skip-opencua", action="store_true")
    parser.add_argument("--h-steps", action="store_true", help="also read H runs' actions.json")
    parser.add_argument("--matrix-output", type=Path, help="write the Holo3 per-task CSV here")
    parser.add_argument("--ledger", type=Path, default=preregister.DEFAULT_LEDGER)
    parser.add_argument("--trajectory-features", type=Path, help="v2: feature file from v2-tarball")
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


def code_hashes() -> dict[str, Any]:
    files = {}
    for rel in CODE_FILES:
        files[rel] = hashlib.sha256((PROJECT_ROOT / rel).read_bytes()).hexdigest()
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
        }
    return state


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


def run_common(
    args: argparse.Namespace, ctx: audit.FetchContext, receipt: dict[str, Any], commit: str
):
    cases = receipt["cases"]
    rows, lb_info = load_leaderboard(args.cache_dir)
    receipt["inputs"]["leaderboard"] = lb_info
    cases["leaderboard_constants_match_pinned_sheet"] = audit.check_leaderboard_constants(rows)

    pkg = audit.load_verified_package(ctx)
    cases["verified_members_match_sha256sums"] = {
        "status": "PASS",
        "members_checked": len(pkg.member_sha256),
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
    h_features: dict[str, dict[str, v2.TrajectoryFeatures]] = collections.defaultdict(dict)

    def on_actions(tag: str, task: str, entries: Any) -> None:
        features = v2.TrajectoryFeatures(task)
        try:
            v2.parse_actions(features, entries)
        except ValueError:
            features.parsed = False
        h_features[tag][task] = features

    h = audit.load_h_runs(
        ctx, pkg.universe, with_steps=args.h_steps, on_actions=on_actions if args.h_steps else None
    )
    h.features = dict(h_features)
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
    pkg, m, h, _, _ = run_common(args, ctx, receipt, audit.OSWORLD_V1_CONFIG_COMMIT)
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
    results["v2_design"] = v2_design(main, h, args.power_sims_d, args.power_sims_a)
    if not args.skip_opencua:
        sets = opencua(args, ctx, receipt)
        holo3_z = main["mcnemar"]["ge"]["C"]["z"]
        results["external_reference"] = audit.opencua_reference(sets, holo3_z, main["h_pairs"])
    if args.matrix_output:
        receipt["outputs"] = {
            "holo3_matrix_csv_sha256": write_csv(args.matrix_output, matrix_rows(m, h)),
            "holo3_matrix_rows": len(m.tasks),
        }


def signature_calibration(h: audit.HRuns) -> dict[str, Any]:
    """How often rule (b)'s text and step signatures fire on the H Company runs.

    The H runs are already inspected and are not v2's confirmatory data, so they
    can show whether the frozen signatures are too sensitive. Screenshots are
    not read, so the identical-screenshot criterion is not part of this check.
    """
    out: dict[str, Any] = {"note": "text and step criteria only; no screenshots read"}
    for tag in audit.H_RUN_TAGS:
        features = h.features.get(tag, {})
        rewards = h.rewards[tag]
        groups: dict[str, list[v2.TrajectoryFeatures]] = {"pass": [], "fail": []}
        for task, item in features.items():
            if task in rewards:
                groups["pass" if rewards[task] >= 0.5 else "fail"].append(item)
        out[tag] = {
            outcome: {
                "n": len(items),
                "env_text_any": sum(1 for f in items if f.env_text_hits),
                "tool_error_any": sum(1 for f in items if f.tool_error_entries),
                "step_cap": sum(1 for f in items if f.steps >= v2.STEP_CAP),
                "final_tool_answer": sum(1 for f in items if f.final_tool == "answer"),
                "pattern_trajectories": dict(
                    sorted(collections.Counter(k for f in items for k in f.env_text_hits).items())
                ),
            }
            for outcome, items in groups.items()
        }
        others = [o for o in audit.H_RUN_TAGS if o != tag]
        unique = [
            t
            for t in features
            if t in rewards
            and rewards[t] < 0.5
            and all(h.rewards[o].get(t, 0.0) >= 0.5 for o in others)
        ]
        classes = collections.Counter()
        for t in unique:
            mine = features[t]
            mine.identical_run = 0
            other = h.features.get(others[0], {}).get(t)
            classes[v2.failure_signature(mine, other, None)] += 1
        out[tag]["unique_failures_vs_other_h_runs"] = {
            "tasks": len(unique),
            "classes": dict(sorted(classes.items())),
        }
    return out


def v2_design(main: dict[str, Any], h: audit.HRuns, sims_d: int, sims_a: int) -> dict[str, Any]:
    """Power for v2 rules (a) and (d) from already-inspected inputs only."""
    clean = main["mcnemar"]["ge"]["clean"]
    design: dict[str, Any] = {
        "label": "v2 design inputs from already-inspected data (v1 totals, H runs)",
        "rule_d_power": v2.power_rule_d(
            n_clean=clean["n"], run1_only=clean["a_only"], run2_only=clean["b_only"], sims=sims_d
        ),
    }
    if all(h.steps.get(tag) for tag in audit.H_RUN_TAGS):
        pairs: list[tuple[int, int]] = []
        baseline = []
        for a_tag, b_tag in itertools.combinations(audit.H_RUN_TAGS, 2):
            a, b = h.steps[a_tag], h.steps[b_tag]
            common = sorted(set(a) & set(b))
            pairs += [(a[t], b[t]) for t in common]
            x = [a[t] for t in common]
            y = [b[t] for t in common]
            ratios = [p / q for p, q in zip(x, y, strict=True) if p > 0 and q > 0]
            baseline.append(
                {
                    "pair": [a_tag, b_tag],
                    "n": len(common),
                    "median_ratio": float(stats.scoreatpercentile(ratios, 50)),
                    "wilcoxon_p": float(stats.wilcoxon(x, y).pvalue) if x != y else 1.0,
                    "identical_step_counts": sum(1 for p, q in zip(x, y, strict=True) if p == q),
                }
            )
        design["h_step_baseline"] = baseline
        design["rule_b_calibration_on_h_runs"] = signature_calibration(h)
        design["rule_a_power"] = v2.power_rule_a(pairs, n=clean["n"], sims=sims_a)
    return design


def stage_v2(args: argparse.Namespace, ctx: audit.FetchContext, receipt: dict[str, Any]) -> None:
    if not receipt["preregistrations"]["v2"]["ledger"]["frozen"]:
        raise GateRefused(f"{v2.V2_EXPERIMENT_ID} is not frozen in the ledger")
    pkg, m, h, configs, _ = run_common(args, ctx, receipt, audit.OSWORLD_V2_CONFIG_COMMIT)
    s1 = {t: v for t, v in m.s1.items() if v is not None}
    s2 = {t: v for t, v in m.s2.items() if v is not None}
    common = [t for t in m.tasks if t in s1 and t in s2]
    clean = [t for t in common if not ((m.flags[t][0] | m.flags[t][1]) - {"F1"})]
    classes = {t: v2.classify_evaluator(configs[t]) for t in m.tasks}
    labels = {t: c.label for t, c in classes.items()}
    results = receipt["results"]
    results["evaluator_classes"] = {
        "counts_all": dict(sorted(collections.Counter(labels.values()).items())),
        "per_task": {t: {"class": c.label, "reasons": list(c.reasons)} for t, c in classes.items()},
    }
    d = v2.rule_d(labels, s1, s2, clean)
    abc = None
    if args.trajectory_features:
        payload = json.loads(args.trajectory_features.read_text())
        features = {
            key: v2.TrajectoryFeatures.from_public(item)
            for key, item in payload["features"].items()
        }
        abc = v2.rules_abc(
            features=features,
            status1=m.v1,
            status2=m.v2,
            s1=s1,
            s2=s2,
            clean=clean,
            h_rewards=h.rewards,
        )
        receipt["inputs"]["trajectory_features_sha256"] = hashlib.sha256(
            args.trajectory_features.read_bytes()
        ).hexdigest()
        # Registered sensitivity: drop every task whose run1 or run2 trajectory
        # lies in the tarball region read before registration.
        probed = {k for k, f in features.items() if (f.compressed_offset or 0) < v2.PROBE_BYTES}
        unprobed = [
            t
            for t in clean
            if str((m.v1[t] or {}).get("trajectory_id")) not in probed
            and str((m.v2[t] or {}).get("trajectory_id")) not in probed
        ]
        keep = set(unprobed) | (set(s1) - set(clean))
        probe_abc = v2.rules_abc(
            features=features,
            status1=m.v1,
            status2=m.v2,
            s1={t: v for t, v in s1.items() if t in keep},
            s2={t: v for t, v in s2.items() if t in keep},
            clean=unprobed,
            h_rewards=h.rewards,
        )
        main_decisions = v2.v2_decisions(d, abc)
        probe_decisions = v2.v2_decisions(d, probe_abc)
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
        "rules_abc": abc,
        "decisions": v2.v2_decisions(d, abc),
    }
    if not args.skip_opencua:
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
    if not receipt["preregistrations"]["v2"]["ledger"]["frozen"]:
        raise GateRefused(f"{v2.V2_EXPERIMENT_ID} is not frozen in the ledger")
    if not args.allow_large_download or args.tarball_dir is None:
        raise GateRefused("v2-tarball needs --allow-large-download and --tarball-dir")
    pkg = audit.load_verified_package(ctx)
    source = ctx.source(audit.VERIFIED_ARCHIVE)
    (member,) = remote_zip.select(
        ctx.listing(audit.VERIFIED_ARCHIVE), [audit.VERIFIED_ROOT + audit.TARBALL_RELPATH]
    )
    dest = args.tarball_dir / "trajectories.tar.gz"
    if not dest.exists():
        receipt["results"]["tarball"] = v2.download_stored_member(
            source, member, dest, expected_sha256=str(pkg.tarball["sha256_from_sha256sums"])
        )
    features = v2.scan_trajectory_tarball(dest)
    wanted = {
        str(record.get("trajectory_id"))
        for run in ("run1", "repair", "run2")
        for record in pkg.status[run].values()
        if record.get("trajectory_id")
    }
    public = {k: f.public() for k, f in sorted(features.items()) if k in wanted}
    out = args.tarball_dir / "trajectory_features.json"
    _atomic_write(out, json.dumps({"features": public}, sort_keys=True).encode())
    receipt["results"]["tarball_scan"] = {
        "trajectories_in_tarball": len(features),
        "trajectories_matching_status_files": len(public),
        "status_trajectory_ids": len(wanted),
        "feature_file_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def overall_status(cases: dict[str, Any]) -> str:
    return "PASS" if all(c.get("status") == "PASS" for c in cases.values()) else "FAIL"


def main(argv: list[str] | None = None, *, context_factory=make_context) -> int:
    args = parse_args(argv)
    started = time.time()
    ctx, transfer = context_factory(args)
    stage_key = "v1" if args.stage == "v1" else "v2"
    receipt: dict[str, Any] = {
        "doctor": DOCTOR_NAME,
        "stage": args.stage,
        "label": "POST-HOC" if args.stage == "v1" else "v2",
        "evidence_grade": EVIDENCE_GRADE[stage_key],
        "started_at": datetime.now(UTC).isoformat(),
        "code": code_hashes(),
        "preregistrations": {
            "v1_posthoc": prereg_state(V1_EXPERIMENT_ID, V1_PREREG, args.ledger),
            "v2": prereg_state(v2.V2_EXPERIMENT_ID, V2_PREREG, args.ledger),
        },
        "parameters": {
            "seeds": args.seeds,
            "sign_flip_draws": args.sign_flip_draws,
            "model_draws": args.model_draws,
            "power_sims": {"rule_d": args.power_sims_d, "rule_a": args.power_sims_a},
            "max_workers": args.max_workers,
            "h_steps": args.h_steps,
            "opencua": not args.skip_opencua,
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
    code = 0
    try:
        {"v1": stage_v1, "v2": stage_v2, "v2-tarball": stage_v2_tarball}[args.stage](
            args, ctx, receipt
        )
        receipt["status"] = overall_status(receipt["cases"]) if receipt["cases"] else "PASS"
        code = 0 if receipt["status"] == "PASS" else 1
    except GateRefused as exc:
        receipt["status"] = "REFUSED"
        receipt["error"] = audit.scrub(str(exc))
        code = 3
    except (
        remote_zip.RemoteZipError,
        osworld_source.SourceFetchError,
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
