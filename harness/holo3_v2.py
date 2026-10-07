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
# Nominal family-wise rate over rules (a), (b) and (d) (Bonferroni bound; D15).
NOMINAL_FAMILY_WISE_RATE = ALPHA_D + ALPHA_A + 2 * ALPHA_B
SHARE_BAR = 0.5  # rule (d) net share in L; rule (b) class shares
SHIFT_LOG_THRESHOLD = math.log(1.10)  # rule (a): |mean log step ratio| >= log 1.10
COVERAGE_BAR = 0.95  # rule (c)
FINAL_WINDOW_DAYS = 14

# ---- Pinned inputs asserted in code (defence in depth over the LFS pin) --- #

# The trajectory tarball as section 1 of the registration states it.
TARBALL_SIZE = 5_748_726_271
TARBALL_CRC32 = 0xC5D5275E
TARBALL_SHA256 = "3d6d65d1842f827494fb19fa4431bfe77f3b3430f3a7edf7673f928d114ffccd"
# Config blob manifest of the 361 task configs v1 read at c7e54d24; v2 reads
# them at f7230379, whose evaluation_examples/ is the same git tree.
V1_CONFIG_BLOB_MANIFEST = "3d4ae6da235e1d6627e72b389cda9fead93dbe9966ac8a3a3e23a1f39762bbf1"

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


def _stratum_pmf(n: int, k: int, n_l: int) -> np.ndarray:
    """P(run1-only tasks in L = a), a = 0 .. min(k, n_l), under Hypergeom(n, k, n_l)."""
    lo, hi = max(0, n_l + k - n), min(k, n_l)
    pmf = np.zeros(hi + 1)
    pmf[lo:] = stats.hypergeom(n, k, n_l).pmf(np.arange(lo, hi + 1))
    return pmf


def _null_sum_distribution(margins: Sequence[tuple[int, int, int]]) -> np.ndarray:
    """P(sum of per-stratum hypergeometric counts = t), t = 0, 1, ...

    Each stratum is (tasks, run1-only tasks, L tasks); under conditional
    independence the run1-only count in L is Hypergeom(tasks, run1-only, L).
    """
    dist = np.array([1.0])
    for n, k, n_l in margins:
        dist = np.convolve(dist, _stratum_pmf(n, k, n_l))
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
# Carried by every rule (d) output (pre-freeze audit; D15): all configs and
# outcomes were on disk while the rule list was written.
RULE_D_BLINDING_NOTE = "blinding to the class-outcome join is self-attested"


def max_attainable_net(tasks: int, run1_only: int, run2_only: int, n_l: int) -> int:
    """Largest net (run1-only minus run2-only) that n_l L tasks of one stratum can hold."""
    return min(n_l, run1_only) - max(0, n_l - (tasks - run2_only))


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
    attainable = sum(
        max_attainable_net(s["tasks"], s["run1_only"], s["run2_only"], s["L"])
        for s in strata.values()
    )
    return {
        "blinding": RULE_D_BLINDING_NOTE,
        "strata": strata,
        "stratified_exact_one_sided_p": p,
        "unstratified_table_L_vs_rest_by_run1_only": table,
        "unstratified_fisher_one_sided_p_descriptive": fisher_one_sided(table),
        "net_flips_all": net_all,
        "net_flips_L": net_l,
        "share_of_net_in_L": (net_l / net_all) if net_all else None,
        "max_attainable_share_of_net_in_L": (attainable / net_all) if net_all else None,
        "by_class": by_class,
    }


RULE_D_LABELS = (
    "checker-side time-drift candidate",  # enriched in L and L carries >= half the net gap
    "checker-side enrichment, minority of the gap",  # enriched, but L carries < half
    "not attributable to checker time-dependence",  # no enrichment at ALPHA_D
)
CHECKER_SIDE_LABELS = RULE_D_LABELS[:2]


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
# Exact, case-sensitive key names; the value must be non-empty (not null,
# false, zero, an empty string, an empty list or an empty object).
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
    image_count: int | None = None  # set when loaded from a feature file

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
            image_count=int(data.get("images", 0)),
        )

    def n_images(self) -> int:
        """Screenshots matched to this trajectory under the registered member layout."""
        return self.image_count if self.image_count is not None else len(self.image_digests)

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
        out.pop("image_count")
        out["images"] = self.n_images()
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
    """A key named exactly as in ERROR_KEYS, at any depth, with a non-empty value.

    Non-empty is JSON truthiness: null, false, 0, "", [] and {} do not count.
    """
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in ERROR_KEYS and bool(item):
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
        # Each field is matched on its own, so no match spans two fields; a
        # label counts once per entry.
        texts = [str(entry[k]) for k in TEXT_FIELDS if entry.get(k) is not None]
        for label, pattern in ENV_TEXT_PATTERNS:
            if any(pattern.search(text) for text in texts):
                env[label] += 1
        if _has_error_key(entry):
            features.tool_error_entries += 1
    features.tools = dict(sorted(tools.items()))
    features.env_text_hits = dict(sorted(env.items()))
    features.parsed = True


def scan_trajectory_tarball(
    path: Path, layout: dict[str, int] | None = None
) -> dict[str, TrajectoryFeatures]:
    """Stream the tar.gz once; keep trajectory ids and derived numbers only.

    The registered member layout is ``<trajectory id>/actions.json(.gz)`` and
    ``<trajectory id>/images/<index>.png(.gz)`` at any depth. ``layout``, if
    given, receives member counts (no names), so a layout that differs from
    the registered one shows up in the receipt instead of silently.
    """
    features: dict[str, TrajectoryFeatures] = {}
    counts = Counter[str]()
    with path.open("rb") as stream, tarfile.open(fileobj=stream, mode="r|gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            counts["file_members"] += 1
            actions = TAR_ACTIONS.search(member.name)
            image = None if actions else TAR_IMAGE.search(member.name)
            if not actions and not image:
                counts["other_file_members"] += 1
                continue
            counts["actions_members" if actions else "image_members"] += 1
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
    if layout is not None:
        for key in ("file_members", "actions_members", "image_members", "other_file_members"):
            layout[key] = counts[key]
        layout["trajectories_with_actions"] = sum(
            1 for f in features.values() if f.compressed_offset is not None
        )
        layout["trajectories_with_images"] = sum(1 for f in features.values() if f.image_digests)
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
    # Registered sensitivity (pre-freeze audit): the known run1-only vs
    # run2-only imbalance pairs passing with failing episodes, and failing
    # episodes are longer, so outcome discordance alone moves m. Concordant
    # clean tasks (same outcome in both runs) carry no such offset.
    concordant = [(a, b) for t, a, b in pairs if (s1[t] >= 0.5) == (s2[t] >= 0.5)]
    rule_a_concordant = {
        "n_pairs": len(concordant),
        **step_shift(
            np.array([a.steps for a, _ in concordant], float),
            np.array([b.steps for _, b in concordant], float),
        ),
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
    specificity_by_run: dict[str, dict[str, float | None]] = {}
    for run, status in (("run1", status1), ("run2", status2)):
        items = [f for f in (feat(status[t]) for t in both_pass) if f is not None]
        specificity_by_run[run] = {
            name: (sum(1 for f in items if env_criteria(f)[name]) / len(items) if items else None)
            for name in ENV_CRITERIA
        }
    # The screenshot criterion depends on the registered image layout; if no
    # joined episode has a matched screenshot it cannot fire, and the
    # all-criteria sensitivity would silently equal the primary.
    joined_features = [f for f in (feat(record) for _, record in episodes) if f is not None]
    with_screenshots = sum(1 for f in joined_features if f.n_images())

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

    all_criteria = labelled(ENV_CRITERIA, False)
    if not with_screenshots:
        all_criteria["verdict"] = SCREENSHOTS_NOT_RUN
    return {
        "rule_c_coverage": {
            "scored_episodes": len(episodes),
            "joined_and_parsed": joined,
            "fraction": coverage,
            "coverage_ok": coverage_ok,
        },
        "rule_a_steps": rule_a,
        "rule_a_steps_concordant_tasks": rule_a_concordant,
        "rule_b_specificity": {
            "both_pass_episodes": len(pass_episodes),
            "share_firing": specificity,
            "share_firing_by_run_descriptive": specificity_by_run,
            "limit": SPECIFICITY_LIMIT,
            "criteria_in_force": list(in_force),
        },
        "rule_b_screenshots": {"joined_episodes_with_screenshots": with_screenshots},
        "rule_b_primary": labelled(in_force, False),
        "rule_b_run1_unique_failures": classify("run1", in_force, False),
        "rule_b_sensitivity_all_criteria": all_criteria,
        "rule_b_sensitivity_step_cap_first": labelled(in_force, True),
    }


SCREENSHOTS_NOT_RUN = "NOT RUN (no joined episode has a screenshot under the registered layout)"


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
                    "power": round(power, 6),
                    "power_test_alone": round(test_only, 6),
                }
            )
    return rows


def size_rule_d_all_allocations(
    strata: Mapping[str, Mapping[str, int]], *, step: tuple[int, int] = (1, 1)
) -> dict[str, Any]:
    """Largest false-positive rate of rule (d)'s test over allocations of L.

    For every (L tasks in web, L tasks offline) on the grid, the exact size of
    the stratified test given the known margins: P(p < ALPHA_D) when run1-only
    tasks fall in L at random. The candidate label (which also needs the share
    bar) cannot fire more often. Exact, no random numbers.
    """
    web, off = strata["web"], strata["offline"]
    pmf_web = {
        n_l: _stratum_pmf(web["tasks"], web["run1_only"], n_l)
        for n_l in range(0, web["tasks"] + 1, step[0])
    }
    pmf_off = {
        n_l: _stratum_pmf(off["tasks"], off["run1_only"], n_l)
        for n_l in range(0, off["tasks"] + 1, step[1])
    }
    worst, at = 0.0, (0, 0)
    for (l_web, a), (l_off, b) in itertools.product(pmf_web.items(), pmf_off.items()):
        null = np.convolve(a, b)
        tail = np.cumsum(null[::-1])[::-1]
        size = float(null[tail < ALPHA_D].sum())
        if size > worst:
            worst, at = size, (l_web, l_off)
    return {
        "allocations": len(pmf_web) * len(pmf_off),
        "grid_step": list(step),
        "max_size": round(worst, 6),
        "max_size_at": list(at),
        "alpha": ALPHA_D,
    }


RULE_A_SCENARIOS: tuple[tuple[float, float], ...] = (
    (1.0, 1.0),
    (1.0, 1.05),
    (1.0, 1 / 1.05),
    (1.0, 1.10),
    (1.0, 1 / 1.10),
    (1.0, 1.15),
    (1.0, 1 / 1.15),
    (1.0, 1.20),
    (1.0, 1 / 1.20),
    (0.2, 2.0),
    (0.2, 0.5),
    (0.3, 1.5),
    (0.3, 0.5),
    (0.4, 1.5),
    (0.4, 0.5),
)


def _shift(rng: np.random.Generator, steps: np.ndarray, fraction: float, ratio: float):
    """Scale ``steps`` by ``ratio`` on a random ``fraction`` of tasks; round; cap."""
    n = len(steps)
    shifted = rng.random(n) < fraction if fraction < 1 else np.ones(n, bool)
    factor = np.where(shifted, ratio, 1.0)
    return np.minimum(STEP_CAP, np.maximum(1, np.round(steps * factor)))


def power_rule_a(
    base_pairs: Sequence[tuple[int, int]],
    *,
    n: int,
    scenarios: Sequence[tuple[float, float]] = RULE_A_SCENARIOS,
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
                b = _shift(rng, sample[:, 1], fraction, ratio)
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


OUTCOME_CATEGORIES = ("both_pass", "both_fail", "run1_only", "run2_only")


def outcome_pools(
    steps: Mapping[str, Mapping[str, int]], rewards: Mapping[str, Mapping[str, float]]
) -> dict[str, list[tuple[int, int]]]:
    """Rerun step-count pairs grouped by the two runs' outcomes.

    Over every pair of runs and every task both scored with a parsed
    trajectory: concordant pairs enter their pool in both orientations (rerun
    order is arbitrary); a discordant pair enters ``run1_only`` as (passing
    steps, failing steps) and ``run2_only`` as (failing, passing).
    """
    pools: dict[str, list[tuple[int, int]]] = {c: [] for c in OUTCOME_CATEGORIES}
    for a_tag, b_tag in itertools.combinations(list(steps), 2):
        a_steps, b_steps = steps[a_tag], steps[b_tag]
        a_rew, b_rew = rewards[a_tag], rewards[b_tag]
        for t in sorted(set(a_steps) & set(b_steps) & set(a_rew) & set(b_rew)):
            sa, sb = a_steps[t], b_steps[t]
            ya, yb = a_rew[t] >= 0.5, b_rew[t] >= 0.5
            if ya == yb:
                pools["both_pass" if ya else "both_fail"] += [(sa, sb), (sb, sa)]
            else:
                passing, failing = (sa, sb) if ya else (sb, sa)
                pools["run1_only"].append((passing, failing))
                pools["run2_only"].append((failing, passing))
    return pools


def power_rule_a_by_outcome(
    pools: Mapping[str, Sequence[tuple[int, int]]],
    counts: Mapping[str, int],
    *,
    scenarios: Sequence[tuple[float, float]] = RULE_A_SCENARIOS,
    sims: int = 400,
    seeds: Sequence[int] = (42, 43, 44),
) -> list[dict[str, Any]]:
    """Power of rule (a) given the clean set's known outcome pattern.

    ``counts`` holds the clean tasks per outcome category (known before
    registration: both pass, both fail, run1-only, run2-only). Each simulated
    task draws a rerun step pair from the pool of its category, so the known
    discordance (failing episodes paired with passing ones) is built in. Then
    run2's steps are shifted as in :func:`power_rule_a`. Reports the primary
    decision (all clean tasks), the registered concordant-task sensitivity,
    how often they differ, and the mean m of each.
    """
    arrays = {c: np.asarray(pools[c], float).reshape(-1, 2) for c in OUTCOME_CATEGORIES}
    for c in OUTCOME_CATEGORIES:
        if counts.get(c, 0) and not len(arrays[c]):
            raise ValueError(f"no rerun pairs for outcome category {c}")
    concordant = np.concatenate(
        [np.full(counts.get(c, 0), c in ("both_pass", "both_fail")) for c in OUTCOME_CATEGORIES]
    )
    rows = []
    for fraction, ratio in scenarios:
        per_seed: dict[str, list[float]] = {
            key: [] for key in ("primary", "concordant", "differ", "m", "m_concordant")
        }
        for seed in seeds:
            rng = np.random.default_rng(seed)
            tally = dict.fromkeys(per_seed, 0.0)
            for _ in range(sims):
                sample = np.concatenate(
                    [
                        arrays[c][rng.integers(0, len(arrays[c]), size=counts[c])]
                        for c in OUTCOME_CATEGORIES
                        if counts.get(c, 0)
                    ]
                )
                a = sample[:, 0]
                b = _shift(rng, sample[:, 1], fraction, ratio)
                primary = step_shift(a, b)
                conc = step_shift(a[concordant], b[concordant])
                hit, hit_c = rule_a_decision(primary), rule_a_decision(conc)
                tally["primary"] += hit
                tally["concordant"] += hit_c
                tally["differ"] += hit != hit_c
                tally["m"] += primary["mean_log_ratio_run1_over_run2"]
                tally["m_concordant"] += conc["mean_log_ratio_run1_over_run2"]
            for key in per_seed:
                per_seed[key].append(tally[key] / sims)
        rows.append(
            {
                "fraction_of_tasks_shifted": fraction,
                "run2_step_factor": round(ratio, 4),
                "power_by_seed": dict(zip(map(str, seeds), per_seed["primary"], strict=True)),
                "power_mean": float(np.mean(per_seed["primary"])),
                "power_mean_concordant_tasks": float(np.mean(per_seed["concordant"])),
                "decisions_differ_mean": float(np.mean(per_seed["differ"])),
                "mean_m": float(np.mean(per_seed["m"])),
                "mean_m_concordant_tasks": float(np.mean(per_seed["m_concordant"])),
            }
        )
    return rows


def power_rule_b(
    n: int,
    thresholds: Mapping[str, int | None],
    *,
    shares: Sequence[float] = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9),
    reference: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Exact power of rule (b)'s labels on ``n`` classified unique failures.

    With the registered reference fixed, each label fires at a count
    threshold. If each failure falls in the class with probability ``share``
    (and, for the agent-side label, none is an environment failure), power is
    the binomial upper tail at the threshold. With ``reference``, a row at the
    reference's own class share gives the label rate when run2's unique
    failures look like the reruns' (the reference itself held fixed).
    """
    rows = []
    for key in ("environment", "agent_side"):
        k = thresholds.get(key)
        grid = [(float(share), False) for share in shares]
        if reference is not None and reference.get("tasks"):
            grid.insert(0, (reference[key] / reference["tasks"], True))
        for share, at_reference in grid:
            power = float(stats.binom.sf(k - 1, n, share)) if k is not None else 0.0
            rows.append(
                {
                    "class": key,
                    "share": round(share, 6),
                    "at_reference_share": at_reference,
                    "threshold": k,
                    "power": round(power, 6),
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
            "nominal_family_wise_rate_a_b_d": NOMINAL_FAMILY_WISE_RATE,
            "scheme": "fixed Bonferroni split; (d) and (a) are judged alone",
        },
        "rule_d": rule_d_decision(rule_d_result),
        "rule_d_blinding": RULE_D_BLINDING_NOTE,
    }
    robust: bool | None = None
    if rule_d_narrow is not None:
        out["rule_d_narrow_L_sensitivity"] = rule_d_decision(rule_d_narrow)
        robust = out["rule_d_narrow_L_sensitivity"] == out["rule_d"]
        out["rule_d_robust_to_L_definition"] = robust
    # D15: a checker-side label that the narrow-L sensitivity does not
    # reproduce is reported as exploratory.
    out["rule_d_evidence"] = (
        "EXPLORATORY (checker-side label not robust to the narrow-L sensitivity; D15)"
        if out["rule_d"] in CHECKER_SIDE_LABELS and robust is not True
        else "CONFIRMATORY"
    )
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
    out["rule_a"] = rule_a_label(abc["rule_a_steps"])
    if "rule_a_steps_concordant_tasks" in abc:
        out["rule_a_sensitivity_concordant_tasks"] = rule_a_label(
            abc["rule_a_steps_concordant_tasks"]
        )
        out["rule_a_robust_to_concordant_tasks"] = (
            out["rule_a_sensitivity_concordant_tasks"] == out["rule_a"]
        )
    out["rule_b"] = abc["rule_b_primary"]["verdict"]
    out["rule_b_sensitivity_all_criteria"] = abc["rule_b_sensitivity_all_criteria"]["verdict"]
    out["rule_b_sensitivity_step_cap_first"] = abc["rule_b_sensitivity_step_cap_first"]["verdict"]
    out["rule_b_robust_to_class_order"] = out["rule_b_sensitivity_step_cap_first"] == out["rule_b"]
    return out


def rule_a_label(result: Mapping[str, Any]) -> str:
    return "agent-behaviour shift" if rule_a_decision(result) else "no agent-behaviour shift"
