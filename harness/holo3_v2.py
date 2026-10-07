"""Holo3 rerun audit v2: rules frozen before the data they test is read.

Rule (d) classifies every task's OSWorld evaluator, from its config JSON
alone, as

* ``L`` - the verdict for a fixed final VM state can change with evaluation
  time: a getter loads a live web page at evaluation time, an expected value
  is computed from the clock, a metric reads the clock, or evaluator
  post-configuration opens a live URL;
* ``W`` - not L, but the task touches the live web (v1's URL flag);
* ``O`` - otherwise,

and tests whether run1-only passes are enriched in L *within* v1's URL strata,
so the URL split already known before registration cannot drive the test.
Rules (a)-(c) read the verified-run trajectory tarball: per-trajectory step
counts, tool use, text signatures of environment trouble, and runs of
identical screenshots. Rule (b) compares the run2-unique failures with the
unique failures of three exchangeable H Company reruns. Paths inside the
tarball contain a personal directory name, so the scanner keeps only
trajectory ids and derived numbers.

The classification rule list below is part of the v2 registration
(``program/preregistrations/q2-holo3-rerun-audit-v2.md``). Changing it after
the freeze is a new registration.
"""

from __future__ import annotations

import gzip
import hashlib
import itertools
import json
import math
import os
import re
import tarfile
import zlib
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

from harness import remote_zip
from harness.holo3_rerun_audit import ALLOWED_URL, URL, web_dependent

V2_EXPERIMENT_ID = "q2-holo3-rerun-audit-v2"

# ---- Error rates (fixed; no threshold depends on whether another test ran) - #

ALPHA_D = 0.04  # rule (d); with ALPHA_A a Bonferroni split of 0.05
ALPHA_A = 0.01  # rule (a); v1's threshold for a behaviour shift
ALPHA_B = 0.025  # each of rule (b)'s two reference comparisons (Bonferroni within (b))
SHARE_BAR = 0.5  # rule (d) net share in L; rule (b) class shares
SHIFT_LOG_THRESHOLD = math.log(1.10)  # rule (a): |mean log step ratio| >= log 1.10
COVERAGE_BAR = 0.95  # rule (c)
FINAL_WINDOW_DAYS = 14

# ---- Rule (d): evaluator classes (frozen with the v2 registration) -------- #

LIVE_OR_CLOCK_GETTERS = frozenset(
    {
        "rule_relativeTime",  # expected date computed from the clock at evaluation
        "time_diff_range",  # paired with clock-reading metrics
        "info_from_website",  # opens a live URL at evaluation
        "page_info",  # opens a live URL at evaluation
        "active_tab_info",  # reloads the active tab's URL in a new page at evaluation
        "gotoRecreationPage_and_get_html_content",  # navigates a live site at evaluation
        "number_of_search_results",  # loads a live search page at evaluation
        "pdf_from_url",  # loads a live URL and prints it at evaluation
    }
)
LIVE_IF_REMOTE_URL_GETTERS = frozenset({"cloud_file"})  # downloads its URL at evaluation
CLOCK_METRICS = frozenset({"compare_time_in_speedtest_results"})  # reads the evaluator clock
CLOCK_RULE_KEYS = frozenset({"relativeTime"})
# The reviewed plan's narrower L ("expected value obtained at evaluation time
# from a live URL or a relative-time or date rule"): expected-side getters
# only. Registered as a sensitivity analysis of rule (d).
NARROW_EXPECTED_GETTERS = LIVE_OR_CLOCK_GETTERS - {"time_diff_range"}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [value]


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def _remote_urls(value: Any) -> list[str]:
    return [u for u in URL.findall(json.dumps(value)) if not ALLOWED_URL.match(u)]


@dataclass(frozen=True)
class EvaluatorClass:
    label: str  # "L", "W" or "O"
    reasons: tuple[str, ...]
    getter_types: tuple[str, ...]
    metric_funcs: tuple[str, ...]
    narrow_l: bool  # the plan's narrower L (registered sensitivity)


def classify_evaluator(config: Mapping[str, Any]) -> EvaluatorClass:
    """Classify one task config. Reads only the config JSON."""
    evaluator = config.get("evaluator") or {}
    expected = [g for g in _as_list(evaluator.get("expected")) if isinstance(g, Mapping)]
    getters = [g for side in ("result", "expected") for g in _as_list(evaluator.get(side))]
    getter_types = tuple(sorted({str(g.get("type")) for g in getters if isinstance(g, Mapping)}))
    funcs = tuple(sorted({str(f) for f in _as_list(evaluator.get("func"))}))
    reasons: list[str] = []
    for getter in getters:
        if not isinstance(getter, Mapping):
            continue
        kind = str(getter.get("type"))
        if kind in LIVE_OR_CLOCK_GETTERS:
            reasons.append(f"getter:{kind}")
        if kind in LIVE_IF_REMOTE_URL_GETTERS and _remote_urls(getter):
            reasons.append(f"getter:{kind}:remote-url")
    reasons += [f"metric:{f}" for f in funcs if f in CLOCK_METRICS]
    if CLOCK_RULE_KEYS & set(_walk_keys(evaluator)):
        reasons.append("rule:relativeTime")
    if _remote_urls(evaluator.get("postconfig")):
        reasons.append("postconfig:remote-url")
    narrow = any(
        str(g.get("type")) in NARROW_EXPECTED_GETTERS
        or (str(g.get("type")) in LIVE_IF_REMOTE_URL_GETTERS and _remote_urls(g))
        for g in expected
    ) or bool(CLOCK_RULE_KEYS & set(_walk_keys(expected)))
    if reasons:
        label = "L"
    elif web_dependent(config):
        label = "W"
    else:
        label = "O"
    return EvaluatorClass(label, tuple(sorted(set(reasons))), getter_types, funcs, narrow)


def fisher_one_sided(table: Sequence[Sequence[int]]) -> float:
    return float(stats.fisher_exact(np.asarray(table), alternative="greater").pvalue)


def _null_sum_distribution(margins: Sequence[tuple[int, int, int]]) -> np.ndarray:
    """P(sum of per-stratum hypergeometric counts = t), t = 0, 1, ...

    Each stratum is (tasks, run1-only tasks, L tasks); under conditional
    independence the run1-only count in L is Hypergeom(tasks, run1-only, L).
    """
    dist = np.array([1.0])
    for n, k, n_l in margins:
        lo, hi = max(0, n_l + k - n), min(k, n_l)
        pmf = np.zeros(hi + 1)
        pmf[lo:] = stats.hypergeom(n, k, n_l).pmf(np.arange(lo, hi + 1))
        dist = np.convolve(dist, pmf)
    return dist


def stratified_exact_p(strata: Sequence[tuple[int, int, int, int]]) -> float:
    """One-sided exact conditional (Mantel-Haenszel) test of a common odds ratio > 1.

    Each stratum is (a, tasks, run1-only, L): ``a`` run1-only tasks are in L.
    p = P(sum a >= observed) with every stratum's margins fixed.
    """
    dist = _null_sum_distribution([(n, k, n_l) for _, n, k, n_l in strata])
    observed = sum(a for a, *_ in strata)
    return float(min(1.0, dist[observed:].sum()))


STRATA = ("web", "offline")  # v1's URL flag


def rule_d(
    classes: Mapping[str, str],
    s1: Mapping[str, float],
    s2: Mapping[str, float],
    clean: Sequence[str],
    web: Mapping[str, bool],
) -> dict[str, Any]:
    """Run1-only passes in L vs not L on the v1 clean set, stratified by v1's URL flag."""
    y1 = {t: s1[t] >= 0.5 for t in clean}
    y2 = {t: s2[t] >= 0.5 for t in clean}
    run1_only = {t for t in clean if y1[t] and not y2[t]}
    run2_only = {t for t in clean if y2[t] and not y1[t]}
    strata: dict[str, dict[str, int]] = {}
    for name in STRATA:
        tasks = [t for t in clean if bool(web[t]) == (name == "web")]
        in_l = [t for t in tasks if classes[t] == "L"]
        strata[name] = {
            "tasks": len(tasks),
            "L": len(in_l),
            "run1_only": sum(1 for t in tasks if t in run1_only),
            "run1_only_in_L": sum(1 for t in in_l if t in run1_only),
            "run2_only": sum(1 for t in tasks if t in run2_only),
            "run2_only_in_L": sum(1 for t in in_l if t in run2_only),
        }
    p = stratified_exact_p(
        [(s["run1_only_in_L"], s["tasks"], s["run1_only"], s["L"]) for s in strata.values()]
    )
    in_l = [t for t in clean if classes[t] == "L"]
    rest = [t for t in clean if classes[t] != "L"]
    a = sum(1 for t in in_l if t in run1_only)
    c = sum(1 for t in rest if t in run1_only)
    table = [[a, len(in_l) - a], [c, len(rest) - c]]
    net_all = len(run1_only) - len(run2_only)
    net_l = a - sum(1 for t in in_l if t in run2_only)
    by_class = {
        label: {
            "tasks": sum(1 for t in clean if classes[t] == label),
            "run1_only": sum(1 for t in run1_only if classes[t] == label),
            "run2_only": sum(1 for t in run2_only if classes[t] == label),
        }
        for label in ("L", "W", "O")
    }
    return {
        "strata": strata,
        "stratified_exact_one_sided_p": p,
        "unstratified_table_L_vs_rest_by_run1_only": table,
        "unstratified_fisher_one_sided_p_descriptive": fisher_one_sided(table),
        "net_flips_all": net_all,
        "net_flips_L": net_l,
        "share_of_net_in_L": (net_l / net_all) if net_all else None,
        "by_class": by_class,
    }


RULE_D_LABELS = (
    "checker-side time-drift candidate",  # enriched in L and L carries >= half the net gap
    "checker-side enrichment, minority of the gap",  # enriched, but L carries < half
    "not attributable to checker time-dependence",  # no enrichment at ALPHA_D
)


def rule_d_decision(result: Mapping[str, Any]) -> str:
    if result["stratified_exact_one_sided_p"] >= ALPHA_D:
        return RULE_D_LABELS[2]
    share = result["share_of_net_in_L"]
    return RULE_D_LABELS[0] if share is not None and share >= SHARE_BAR else RULE_D_LABELS[1]


# ---- Rules (a)-(c): trajectory tarball ------------------------------------ #

TRAJECTORY_ID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
TAR_ACTIONS = re.compile(rf"(?:^|/)({TRAJECTORY_ID})/actions\.json(?:\.gz)?$")
TAR_IMAGE = re.compile(rf"(?:^|/)({TRAJECTORY_ID})/images/(\d+)\.png(?:\.gz)?$")
STEP_CAP = 100
# Before registration the scout read the first ~232 MB of the compressed
# tarball and the reviewer the first 8 MB; trajectories whose actions.json is
# reached within this many compressed bytes form the probed region.
PROBE_BYTES = 250_000_000
ENV_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        ("captcha", r"captcha|recaptcha|hcaptcha"),
        ("unusual_traffic", r"unusual traffic"),
        ("access_denied", r"access denied"),
        ("bot_challenge", r"are you a robot|not a robot|verify (?:that )?you are (?:a )?human"),
        ("challenge_page", r"cloudflare|checking your browser|just a moment"),
        ("chrome_net_error", r"\berr_[a-z_]{4,}\b"),
        ("unreachable", r"(?:site|page) can.?t be reached|cannot be reached|could not be reached"),
        ("page_load", r"page (?:failed|fails|did not|didn.?t|is not|isn.?t) (?:to )?load"),
        ("connection", r"connection (?:reset|refused|timed out|was reset|failed|error)"),
        ("offline", r"no internet|you are offline|network error"),
        (
            "http_error",
            r"\b(?:403 forbidden|429 too many requests|502 bad gateway|"
            r"503 service unavailable|504 gateway time-?out)\b",
        ),
        ("rate_limit", r"too many requests|rate limit"),
    )
)
TEXT_FIELDS = ("reasoning", "thought", "note")
ERROR_KEYS = frozenset({"error", "exception", "traceback", "tool_error"})


@dataclass
class TrajectoryFeatures:
    trajectory_id: str
    steps: int = 0
    final_tool: str | None = None
    tools: dict[str, int] = field(default_factory=dict)
    env_text_hits: dict[str, int] = field(default_factory=dict)
    tool_error_entries: int = 0
    image_refs: list[int] = field(default_factory=list)
    image_digests: dict[int, str] = field(default_factory=dict)
    parsed: bool = False
    compressed_offset: int | None = None  # tarball bytes read when actions.json was reached
    identical_run: int | None = None  # set when loaded from a feature file

    @classmethod
    def from_public(cls, data: Mapping[str, Any]) -> TrajectoryFeatures:
        """Rebuild from :meth:`public` output (image digests are not kept)."""
        return cls(
            trajectory_id=str(data["trajectory_id"]),
            steps=int(data["steps"]),
            final_tool=data.get("final_tool"),
            tools=dict(data.get("tools", {})),
            env_text_hits=dict(data.get("env_text_hits", {})),
            tool_error_entries=int(data.get("tool_error_entries", 0)),
            parsed=bool(data["parsed"]),
            compressed_offset=data.get("compressed_offset"),
            identical_run=int(data["max_identical_screenshot_run"]),
        )

    def max_identical_run(self) -> int:
        """Longest run of identical screenshots.

        Order: the order in which ``actions.json`` references the images; if it
        references none, ascending image index (the registered fallback).
        """
        if self.identical_run is not None:
            return self.identical_run
        order = self.image_refs or sorted(self.image_digests)
        best = run = 0
        previous: str | None = None
        for index in order:
            digest = self.image_digests.get(index)
            if digest is not None and digest == previous:
                run += 1
            else:
                run = 1 if digest is not None else 0
            previous = digest
            best = max(best, run)
        return best

    def public(self) -> dict[str, Any]:
        out = asdict(self)
        out.pop("image_digests")
        out.pop("image_refs")
        out.pop("identical_run")
        out["images"] = len(self.image_digests)
        out["max_identical_screenshot_run"] = self.max_identical_run()
        return out


def _tool_name(action: Any) -> str | None:
    if isinstance(action, Mapping):
        name = action.get("tool_name")
        return str(name) if name is not None else None
    if isinstance(action, str):
        match = re.search(r"['\"]tool_name['\"]\s*:\s*['\"]([^'\"]+)", action)
        return match.group(1) if match else None
    return None


def _has_error_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in ERROR_KEYS and item not in (None, "", [], {}):
                return True
            if _has_error_key(item):
                return True
    elif isinstance(value, list):
        return any(_has_error_key(item) for item in value)
    return False


def parse_actions(features: TrajectoryFeatures, entries: Any) -> None:
    if not isinstance(entries, list):
        raise ValueError("actions.json is not a list")
    tools: Counter[str] = Counter()
    env: Counter[str] = Counter()
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        image = entry.get("image")
        if isinstance(image, str):
            match = re.search(r"(\d+)\.png", image)
            if match:
                features.image_refs.append(int(match.group(1)))
        if "action" in entry:
            features.steps += 1
            name = _tool_name(entry["action"])
            if name:
                tools[name] += 1
                features.final_tool = name
        text = " ".join(str(entry.get(k, "")) for k in TEXT_FIELDS)
        for label, pattern in ENV_TEXT_PATTERNS:
            if pattern.search(text):
                env[label] += 1
        if _has_error_key(entry):
            features.tool_error_entries += 1
    features.tools = dict(sorted(tools.items()))
    features.env_text_hits = dict(sorted(env.items()))
    features.parsed = True


def scan_trajectory_tarball(path: Path) -> dict[str, TrajectoryFeatures]:
    """Stream the tar.gz once; keep trajectory ids and derived numbers only."""
    features: dict[str, TrajectoryFeatures] = {}
    with path.open("rb") as stream, tarfile.open(fileobj=stream, mode="r|gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            actions = TAR_ACTIONS.search(member.name)
            image = None if actions else TAR_IMAGE.search(member.name)
            if not actions and not image:
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            raw = handle.read()
            if member.name.endswith(".gz"):
                raw = gzip.decompress(raw)
            trajectory = (actions or image).group(1)  # type: ignore[union-attr]
            entry = features.setdefault(trajectory, TrajectoryFeatures(trajectory))
            if actions:
                entry.compressed_offset = stream.tell()
                try:
                    parse_actions(entry, json.loads(raw))
                except (ValueError, json.JSONDecodeError):
                    entry.parsed = False
            else:
                entry.image_digests[int(image.group(2))] = hashlib.sha256(raw).hexdigest()  # type: ignore[union-attr]
    return features


def _file_checks(path: Path, member: remote_zip.ZipMember, expected_sha256: str):
    digest = hashlib.sha256()
    crc = 0
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
            crc = zlib.crc32(block, crc)
            size += len(block)
    checks = {
        "size": size == member.file_size,
        "crc32": (crc & 0xFFFFFFFF) == member.crc,
        "sha256": digest.hexdigest() == expected_sha256,
    }
    return checks, {"size": size, "crc32": f"{crc & 0xFFFFFFFF:08x}", "sha256": digest.hexdigest()}


def download_stored_member(
    source: remote_zip.RangeSource,
    member: remote_zip.ZipMember,
    dest: Path,
    *,
    expected_sha256: str,
    chunk: int = 64 << 20,
) -> dict[str, Any]:
    """Resumable download of one STORED member; verifies size, CRC-32 and SHA-256.

    Bytes go to ``dest.with_suffix('.part')``; the final name appears only after
    every check passes. A file already at ``dest`` is re-verified, never trusted.
    Any file that fails a check is removed, so the next attempt starts clean.
    """
    if dest.exists():
        checks, info = _file_checks(dest, member, expected_sha256)
        if not all(checks.values()):
            dest.unlink()
            raise remote_zip.ZipIntegrityError(f"existing file failed checks: {checks}")
        return {**info, "reused_existing_file": True}
    window = remote_zip.stored_member_window(source, member)
    part = dest.with_name(dest.name + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    have = part.stat().st_size if part.exists() else 0
    if have > window.size:
        part.unlink()
        raise remote_zip.ZipIntegrityError("partial download is larger than the member")
    with part.open("ab") as out:
        position = have
        while position < window.size:
            length = min(chunk, window.size - position)
            out.write(window.read_range(position, length))
            position += length
            out.flush()
            os.fsync(out.fileno())
    checks, info = _file_checks(part, member, expected_sha256)
    if not all(checks.values()):
        part.unlink()
        raise remote_zip.ZipIntegrityError(f"downloaded member failed checks: {checks}")
    os.replace(part, dest)
    return {**info, "reused_existing_file": False, "resumed_from_bytes": have}


def unique_failures(
    failing: Mapping[str, float],
    passing: Mapping[str, float],
    h_rewards: Mapping[str, Mapping[str, float]],
    tasks: Sequence[str],
) -> list[str]:
    """Tasks the failing run fails while the other maintainer run and every H run
    that scored the task (at least two) pass."""
    out = []
    for t in tasks:
        h = [r[t] for r in h_rewards.values() if t in r]
        if len(h) < 2:
            continue
        if failing[t] < 0.5 and passing[t] >= 0.5 and all(v >= 0.5 for v in h):
            out.append(t)
    return out


# Rule (b)'s pooled H rerun reference (primary criteria, registered order) as
# computed by the v2-design stage from already-inspected data and registered in
# the v2 draft. The v2 stage recomputes it and fails a positive control if it
# differs.
REGISTERED_H_REFERENCE: dict[str, Any] | None = {
    "tasks": 30,
    "environment": 0,
    "agent_side": 10,
    "classes": {"other": 20, "premature_answer": 1, "step_cap": 9},
}

SPECIFICITY_LIMIT = 0.20
IDENTICAL_SCREENSHOT_RUN = 3
ENV_CRITERIA = ("tool_error", "text", "screenshots")
# Criteria the H rerun reference can also be classified with (its screenshots
# are not read), so only these can decide a rule (b) label.
PRIMARY_ENV_CRITERIA = ("tool_error", "text")
CLASSES = ("environment", "step_cap", "premature_answer", "declared_infeasible", "other")
AGENT_CLASSES = ("step_cap", "premature_answer")


def env_criteria(features: TrajectoryFeatures) -> dict[str, bool]:
    return {
        "tool_error": features.tool_error_entries > 0,
        "text": bool(features.env_text_hits),
        "screenshots": features.max_identical_run() >= IDENTICAL_SCREENSHOT_RUN,
    }


def failure_signature(
    mine: TrajectoryFeatures | None,
    other: TrajectoryFeatures | None,
    status: Mapping[str, Any] | None,
    criteria: Sequence[str] = PRIMARY_ENV_CRITERIA,
    *,
    step_cap_first: bool = False,
) -> str:
    """First matching class in the registered order.

    Registered order: environment, step cap, premature answer, declared
    infeasible, other. ``step_cap_first`` gives the reviewed plan's order
    (step cap before environment), a registered sensitivity. ``criteria`` are
    the environment-signature components in force.
    """
    if mine is None or not mine.parsed:
        return "unclassifiable"
    hits = env_criteria(mine)
    environment = any(hits[name] for name in criteria)
    capped = mine.steps >= STEP_CAP
    if step_cap_first and capped:
        return "step_cap"
    if environment:
        return "environment"
    if capped:
        return "step_cap"
    if other is not None and other.parsed and other.steps and mine.steps <= 0.5 * other.steps:
        return "premature_answer"
    message = str((status or {}).get("agp_message", ""))
    if message.startswith("Infeasible") or "FAIL" in str((status or {}).get("agp_actions", "")):
        return "declared_infeasible"
    return "other"


def composition(labels: Mapping[str, str]) -> dict[str, Any]:
    counts = Counter(labels.values())
    n = len(labels)
    env = counts["environment"]
    agent = sum(counts[c] for c in AGENT_CLASSES)
    return {
        "tasks": n,
        "classes": dict(sorted(counts.items())),
        "environment": env,
        "agent_side": agent,
        "environment_share": env / n if n else None,
        "agent_side_share": agent / n if n else None,
    }


def h_unique_failure_labels(
    h_features: Mapping[str, Mapping[str, TrajectoryFeatures]],
    h_rewards: Mapping[str, Mapping[str, float]],
    tasks: Sequence[str],
    criteria: Sequence[str] = PRIMARY_ENV_CRITERIA,
    *,
    step_cap_first: bool = False,
    runs: Sequence[str] | None = None,
) -> dict[str, dict[str, str]]:
    """Signatures of each H run's unique failures (failed; both siblings passed).

    The comparison trajectory for "premature answer" is the first sibling in
    the registered run order. Missing trajectories are unclassifiable.
    """
    tags = list(h_rewards)
    out: dict[str, dict[str, str]] = {}
    for tag in runs or tags:
        others = [o for o in tags if o != tag]
        labels: dict[str, str] = {}
        for t in tasks:
            reward = h_rewards[tag].get(t)
            if reward is None or reward >= 0.5:
                continue
            if not all(h_rewards[o].get(t) is not None and h_rewards[o][t] >= 0.5 for o in others):
                continue
            mine = h_features.get(tag, {}).get(t)
            other = h_features.get(others[0], {}).get(t)
            labels[t] = failure_signature(
                mine, other, None, criteria, step_cap_first=step_cap_first
            )
        out[tag] = labels
    return out


def rule_b_label(run: Mapping[str, Any], reference: Mapping[str, Any]) -> dict[str, Any]:
    """Rule (b)'s label: a class share >= 0.5 that also exceeds the H rerun reference.

    Each comparison is a one-sided Fisher exact test of the run's class count
    against the pooled reference count, at ALPHA_B; environment is checked first.
    """
    n, big_n = run["tasks"], reference["tasks"]
    p = {
        key: fisher_one_sided([[run[key], n - run[key]], [reference[key], big_n - reference[key]]])
        if n and big_n
        else 1.0
        for key in ("environment", "agent_side")
    }
    if not n:
        verdict = "no unique failures"
    elif run["environment"] / n >= SHARE_BAR and p["environment"] < ALPHA_B:
        verdict = "R1-retro: infrastructure"
    elif run["agent_side"] / n >= SHARE_BAR and p["agent_side"] < ALPHA_B:
        verdict = "agent-side session variation"
    else:
        verdict = "unexplained"
    return {"fisher_one_sided_p_vs_reference": p, "verdict": verdict}


def rule_b_thresholds(n: int, reference: Mapping[str, Any]) -> dict[str, int | None]:
    """Smallest count of n unique failures at which each label can fire."""
    out: dict[str, int | None] = {}
    if not n:
        return {"environment": None, "agent_side": None}
    for key in ("environment", "agent_side"):
        out[key] = next(
            (
                k
                for k in range(n + 1)
                if k / n >= SHARE_BAR
                and fisher_one_sided(
                    [[k, n - k], [reference[key], reference["tasks"] - reference[key]]]
                )
                < ALPHA_B
            ),
            None,
        )
    return out


def pooled(compositions: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items = list(compositions)
    total = {"tasks": 0, "environment": 0, "agent_side": 0}
    classes: Counter[str] = Counter()
    for item in items:
        for key in total:
            total[key] += item[key]
        classes.update(item["classes"])
    n = total["tasks"]
    return {
        **total,
        "classes": dict(sorted(classes.items())),
        "environment_share": total["environment"] / n if n else None,
        "agent_side_share": total["agent_side"] / n if n else None,
    }


def h_reference(
    h_features: Mapping[str, Mapping[str, TrajectoryFeatures]],
    h_rewards: Mapping[str, Mapping[str, float]],
    tasks: Sequence[str],
    criteria: Sequence[str] = PRIMARY_ENV_CRITERIA,
    *,
    step_cap_first: bool = False,
) -> dict[str, Any]:
    labels = h_unique_failure_labels(
        h_features, h_rewards, tasks, criteria, step_cap_first=step_cap_first
    )
    per_run = {tag: composition(v) for tag, v in labels.items()}
    return {"per_run": per_run, "pooled": pooled(per_run.values())}


def rules_abc(
    *,
    features: Mapping[str, TrajectoryFeatures],
    status1: Mapping[str, Mapping[str, Any] | None],
    status2: Mapping[str, Mapping[str, Any] | None],
    s1: Mapping[str, float],
    s2: Mapping[str, float],
    clean: Sequence[str],
    h_rewards: Mapping[str, Mapping[str, float]],
    h_features: Mapping[str, Mapping[str, TrajectoryFeatures]],
) -> dict[str, Any]:
    def feat(record: Mapping[str, Any] | None) -> TrajectoryFeatures | None:
        trajectory = (record or {}).get("trajectory_id")
        found = features.get(str(trajectory)) if trajectory else None
        return found if found is not None and found.parsed else None

    episodes = [(t, status1[t]) for t in s1] + [(t, status2[t]) for t in s2]
    joined = sum(1 for _, record in episodes if feat(record) is not None)
    coverage = joined / len(episodes) if episodes else 0.0
    coverage_ok = coverage >= COVERAGE_BAR

    pairs = [(t, feat(status1[t]), feat(status2[t])) for t in clean]
    pairs = [(t, a, b) for t, a, b in pairs if a is not None and b is not None]
    steps1 = np.array([a.steps for _, a, _ in pairs], float)
    steps2 = np.array([b.steps for _, _, b in pairs], float)
    rule_a = {"n_pairs": len(pairs), **step_shift(steps1, steps2)}
    rule_a["step_cap_hits"] = {
        "run1": int(np.sum(steps1 >= STEP_CAP)),
        "run2": int(np.sum(steps2 >= STEP_CAP)),
    }

    # Specificity guard, applied before any unique failure is classified: an
    # environment criterion that fires on more than 20% of the episodes of
    # clean tasks both runs passed cannot diagnose an environment failure and
    # is dropped from the primary classification.
    both_pass = [t for t in clean if s1[t] >= 0.5 and s2[t] >= 0.5]
    pass_episodes = [
        f for t in both_pass for f in (feat(status1[t]), feat(status2[t])) if f is not None
    ]
    specificity = {
        name: (
            sum(1 for f in pass_episodes if env_criteria(f)[name]) / len(pass_episodes)
            if pass_episodes
            else None
        )
        for name in ENV_CRITERIA
    }
    in_force = tuple(
        name
        for name in PRIMARY_ENV_CRITERIA
        if specificity[name] is not None and specificity[name] <= SPECIFICITY_LIMIT
    )

    def classify(failing_run: str, criteria: Sequence[str], step_cap_first: bool) -> dict:
        if failing_run == "run2":
            tasks = unique_failures(s2, s1, h_rewards, clean)
            mine_status, other_status = status2, status1
        else:
            tasks = unique_failures(s1, s2, h_rewards, clean)
            mine_status, other_status = status1, status2
        labels = {
            t: failure_signature(
                feat(mine_status[t]),
                feat(other_status[t]),
                mine_status[t],
                criteria,
                step_cap_first=step_cap_first,
            )
            for t in tasks
        }
        return composition(labels)

    def labelled(criteria: Sequence[str], step_cap_first: bool) -> dict[str, Any]:
        run = classify("run2", criteria, step_cap_first)
        reference = h_reference(
            h_features, h_rewards, clean, criteria, step_cap_first=step_cap_first
        )
        return {
            "criteria": list(criteria),
            "step_cap_first": step_cap_first,
            "run2_unique_failures": run,
            "h_reference": reference,
            **rule_b_label(run, reference["pooled"]),
        }

    return {
        "rule_c_coverage": {
            "scored_episodes": len(episodes),
            "joined_and_parsed": joined,
            "fraction": coverage,
            "coverage_ok": coverage_ok,
        },
        "rule_a_steps": rule_a,
        "rule_b_specificity": {
            "both_pass_episodes": len(pass_episodes),
            "share_firing": specificity,
            "limit": SPECIFICITY_LIMIT,
            "criteria_in_force": list(in_force),
        },
        "rule_b_primary": labelled(in_force, False),
        "rule_b_run1_unique_failures": classify("run1", in_force, False),
        "rule_b_sensitivity_all_criteria": labelled(ENV_CRITERIA, False),
        "rule_b_sensitivity_step_cap_first": labelled(in_force, True),
    }


def step_shift(steps1: np.ndarray, steps2: np.ndarray) -> dict[str, Any]:
    """Rule (a)'s test and effect size for paired step counts."""
    n = len(steps1)
    positive = (steps1 > 0) & (steps2 > 0)
    log_ratio = np.log(steps1[positive]) - np.log(steps2[positive])
    mean_log = float(np.mean(log_ratio)) if positive.any() else math.nan
    p = float(stats.wilcoxon(steps1, steps2).pvalue) if n and np.any(steps1 != steps2) else 1.0
    return {
        "wilcoxon_p": p,
        "mean_log_ratio_run1_over_run2": mean_log,
        "geometric_mean_ratio_run1_over_run2": math.exp(mean_log) if positive.any() else math.nan,
        "median_ratio_run1_over_run2_descriptive": (
            float(np.median(steps1[positive] / steps2[positive])) if positive.any() else math.nan
        ),
        "median_run1": float(np.median(steps1)) if n else None,
        "median_run2": float(np.median(steps2)) if n else None,
        "tied_pairs": int(np.sum(steps1 == steps2)),
    }


def rule_a_decision(result: Mapping[str, Any]) -> bool:
    mean_log = result["mean_log_ratio_run1_over_run2"]
    return (
        result["wilcoxon_p"] < ALPHA_A
        and math.isfinite(mean_log)
        and abs(mean_log) >= SHIFT_LOG_THRESHOLD
    )


# ---- Design power (inputs are already-inspected data only) ---------------- #


def power_rule_d(
    strata: Mapping[str, Mapping[str, int]],
    *,
    l_tasks: Sequence[tuple[int, int]] = (
        (10, 0),
        (20, 0),
        (30, 0),
        (0, 20),
        (0, 40),
        (10, 20),
        (20, 40),
    ),
    odds_ratios: Sequence[float] = (1.0, 3.0, 5.0, 10.0, 30.0),
) -> list[dict[str, Any]]:
    """Exact power of rule (d) given the stratum margins known before registration.

    ``strata`` holds, per v1 URL stratum, the clean tasks and their run1-only
    and run2-only counts. ``l_tasks`` are (L tasks in web, L tasks offline).
    Under the alternative the run1-only tasks of a stratum fall in L with odds
    ratio ``psi`` (Fisher's noncentral hypergeometric); run2-only tasks fall in
    L at random among the rest. Detection: stratified exact p < ALPHA_D and net
    share >= 0.5. Exact enumeration, no random numbers.
    """
    web, off = strata["web"], strata["offline"]
    net_all = web["run1_only"] + off["run1_only"] - web["run2_only"] - off["run2_only"]
    rows = []
    for n_l_web, n_l_off in l_tasks:
        null = _null_sum_distribution(
            [(web["tasks"], web["run1_only"], n_l_web), (off["tasks"], off["run1_only"], n_l_off)]
        )
        tail = np.cumsum(null[::-1])[::-1]

        def joint(stratum: Mapping[str, int], n_l: int, psi: float):
            n, k, j = stratum["tasks"], stratum["run1_only"], stratum["run2_only"]
            lo, hi = max(0, n_l + k - n), min(k, n_l)
            for a in range(lo, hi + 1):
                # lo == hi: degenerate (no L tasks, or no run1-only tasks)
                pa = 1.0 if lo == hi else float(stats.nchypergeom_fisher(n, k, n_l, psi).pmf(a))
                rest = n_l - a
                b_lo, b_hi = max(0, rest + j - (n - k)), min(j, rest)
                for b in range(b_lo, b_hi + 1):
                    yield a, b, pa * float(stats.hypergeom(n - k, j, rest).pmf(b))

        for psi in odds_ratios:
            power = test_only = 0.0
            for (a_w, b_w, p_w), (a_o, b_o, p_o) in itertools.product(
                list(joint(web, n_l_web, psi)), list(joint(off, n_l_off, psi))
            ):
                prob = p_w * p_o
                if tail[a_w + a_o] < ALPHA_D:
                    test_only += prob
                    if net_all > 0 and (a_w + a_o - b_w - b_o) / net_all >= SHARE_BAR:
                        power += prob
            rows.append(
                {
                    "L_tasks_web": n_l_web,
                    "L_tasks_offline": n_l_off,
                    "odds_ratio": psi,
                    "power": round(power, 4),
                    "power_test_alone": round(test_only, 4),
                }
            )
    return rows


def power_rule_a(
    base_pairs: Sequence[tuple[int, int]],
    *,
    n: int,
    scenarios: Sequence[tuple[float, float]] = (
        (1.0, 1.0),
        (1.0, 1.05),
        (1.0, 1.10),
        (1.0, 1 / 1.10),
        (1.0, 1.15),
        (1.0, 1 / 1.15),
        (1.0, 1.20),
        (0.2, 2.0),
        (0.2, 0.5),
        (0.3, 1.5),
        (0.3, 0.5),
        (0.4, 1.5),
        (0.4, 0.5),
    ),
    sims: int = 400,
    seeds: Sequence[int] = (42, 43, 44),
) -> list[dict[str, Any]]:
    """Power of rule (a) by bootstrapping rerun step-count pairs.

    ``base_pairs`` are (steps, steps) for the same task in two reruns that
    share a harness (the H runs). In each scenario (fraction, ratio) run2's
    steps are scaled by ``ratio`` on a random ``fraction`` of the tasks, rounded
    and capped at the step cap. A detection is rule (a)'s registered decision.
    The superseded median-of-ratios gate is reported alongside for comparison.
    """
    base = np.asarray(base_pairs, float)
    rows = []
    for fraction, ratio in scenarios:
        per_seed, per_seed_old = [], []
        for seed in seeds:
            rng = np.random.default_rng(seed)
            hits = old = 0
            for _ in range(sims):
                sample = base[rng.integers(0, len(base), size=n)]
                a = sample[:, 0]
                shifted = rng.random(n) < fraction if fraction < 1 else np.ones(n, bool)
                factor = np.where(shifted, ratio, 1.0)
                b = np.minimum(STEP_CAP, np.maximum(1, np.round(sample[:, 1] * factor)))
                result = step_shift(a, b)
                if rule_a_decision(result):
                    hits += 1
                median = result["median_ratio_run1_over_run2_descriptive"]
                if result["wilcoxon_p"] < ALPHA_A and abs(median - 1) >= 0.10:
                    old += 1
            per_seed.append(hits / sims)
            per_seed_old.append(old / sims)
        rows.append(
            {
                "fraction_of_tasks_shifted": fraction,
                "run2_step_factor": round(ratio, 4),
                "power_by_seed": dict(zip(map(str, seeds), per_seed, strict=True)),
                "power_mean": float(np.mean(per_seed)),
                "power_mean_superseded_median_gate": float(np.mean(per_seed_old)),
            }
        )
    return rows


def v2_decisions(
    rule_d_result: Mapping[str, Any],
    abc: Mapping[str, Any] | None,
    *,
    rule_d_narrow: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Decision labels. Fixed error rates: no test's threshold depends on another."""
    out: dict[str, Any] = {
        "error_rates": {
            "rule_d": ALPHA_D,
            "rule_a": ALPHA_A,
            "rule_b_each_comparison": ALPHA_B,
            "scheme": "fixed Bonferroni split; (d) and (a) are judged alone",
        },
        "rule_d": rule_d_decision(rule_d_result),
    }
    if rule_d_narrow is not None:
        out["rule_d_narrow_L_sensitivity"] = rule_d_decision(rule_d_narrow)
        out["rule_d_robust_to_L_definition"] = out["rule_d_narrow_L_sensitivity"] == out["rule_d"]
    if abc is None:
        out["rule_a"] = "NOT RUN (trajectory tarball not read)"
        out["rule_b"] = "NOT RUN (trajectory tarball not read)"
        out["rule_c"] = "NOT RUN (trajectory tarball not read)"
        return out
    coverage_ok = abc["rule_c_coverage"]["coverage_ok"]
    out["rule_c"] = (
        "coverage ok" if coverage_ok else "coverage-limited: (a) and (b) descriptive only"
    )
    if not coverage_ok:
        out["rule_a"] = "descriptive only (coverage < 95%)"
        out["rule_b"] = "descriptive only (coverage < 95%)"
        return out
    out["rule_a"] = (
        "agent-behaviour shift"
        if rule_a_decision(abc["rule_a_steps"])
        else "no agent-behaviour shift"
    )
    out["rule_b"] = abc["rule_b_primary"]["verdict"]
    out["rule_b_sensitivity_all_criteria"] = abc["rule_b_sensitivity_all_criteria"]["verdict"]
    out["rule_b_sensitivity_step_cap_first"] = abc["rule_b_sensitivity_step_cap_first"]["verdict"]
    return out
