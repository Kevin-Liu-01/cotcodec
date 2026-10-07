"""Holo3 rerun audit v2: rules frozen before the data they test is read.

Rule (d) classifies every task's OSWorld evaluator, from its config JSON
alone, as

* ``L`` - the verdict for a fixed final VM state can change with evaluation
  time: a getter loads a live web page at evaluation time, an expected value
  is computed from the clock, a metric reads the clock, or evaluator
  post-configuration opens a live URL;
* ``W`` - not L, but the task touches the live web (v1's URL flag);
* ``O`` - otherwise,

and tests whether run1-only passes are enriched in L. Rules (a)-(c) read the
verified-run trajectory tarball: per-trajectory step counts, tool use, text
signatures of environment trouble, and runs of identical screenshots. Paths
inside the tarball contain a personal directory name, so the scanner keeps only
trajectory ids and derived numbers.

The classification rule list below is part of the v2 registration
(``program/preregistrations/q2-holo3-rerun-audit-v2.md``). Changing it after
the freeze is a new registration.
"""

from __future__ import annotations

import gzip
import hashlib
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
from harness.holo3_rerun_audit import ALLOWED_URL, URL, holm, web_dependent

V2_EXPERIMENT_ID = "q2-holo3-rerun-audit-v2"

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


def classify_evaluator(config: Mapping[str, Any]) -> EvaluatorClass:
    """Classify one task config. Reads only the config JSON."""
    evaluator = config.get("evaluator") or {}
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
    if reasons:
        label = "L"
    elif web_dependent(config):
        label = "W"
    else:
        label = "O"
    return EvaluatorClass(label, tuple(sorted(set(reasons))), getter_types, funcs)


def fisher_one_sided(table: Sequence[Sequence[int]]) -> float:
    return float(stats.fisher_exact(np.asarray(table), alternative="greater").pvalue)


def rule_d(
    classes: Mapping[str, str],
    s1: Mapping[str, float],
    s2: Mapping[str, float],
    clean: Sequence[str],
) -> dict[str, Any]:
    """Run1-only passes in L vs W+O on the v1 clean set (y = 1[s >= 0.5])."""
    y1 = {t: s1[t] >= 0.5 for t in clean}
    y2 = {t: s2[t] >= 0.5 for t in clean}
    run1_only = {t for t in clean if y1[t] and not y2[t]}
    run2_only = {t for t in clean if y2[t] and not y1[t]}
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
        "table_L_vs_rest_by_run1_only": table,
        "fisher_one_sided_p": fisher_one_sided(table),
        "net_flips_all": net_all,
        "net_flips_L": net_l,
        "share_of_net_in_L": (net_l / net_all) if net_all else None,
        "by_class": by_class,
    }


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
    every check passes.
    """
    window = remote_zip.stored_member_window(source, member)
    part = dest.with_name(dest.name + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    have = part.stat().st_size if part.exists() else 0
    if have > window.size:
        raise remote_zip.ZipIntegrityError("partial download is larger than the member")
    with part.open("ab") as out:
        position = have
        while position < window.size:
            length = min(chunk, window.size - position)
            out.write(window.read_range(position, length))
            position += length
            out.flush()
            os.fsync(out.fileno())
    digest = hashlib.sha256()
    crc = 0
    size = 0
    with part.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
            crc = zlib.crc32(block, crc)
            size += len(block)
    checks = {
        "size": size == member.file_size,
        "crc32": (crc & 0xFFFFFFFF) == member.crc,
        "sha256": digest.hexdigest() == expected_sha256,
    }
    if not all(checks.values()):
        raise remote_zip.ZipIntegrityError(f"downloaded member failed checks: {checks}")
    os.replace(part, dest)
    return {"size": size, "crc32": f"{member.crc:08x}", "sha256": digest.hexdigest()}


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


SPECIFICITY_LIMIT = 0.20
IDENTICAL_SCREENSHOT_RUN = 3
ENV_CRITERIA = ("tool_error", "text", "screenshots")


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
    criteria: Sequence[str] = ENV_CRITERIA,
) -> str:
    """First matching class in the registered order.

    ``criteria`` are the environment-signature components still in force after
    the specificity guard (see :func:`rules_abc`).
    """
    if mine is None or not mine.parsed:
        return "unclassifiable"
    if mine.steps >= STEP_CAP:
        return "1_step_cap"
    hits = env_criteria(mine)
    if any(hits[name] for name in criteria):
        return "2_environment"
    if other is not None and other.parsed and other.steps and mine.steps <= 0.5 * other.steps:
        return "3_premature_answer"
    message = str((status or {}).get("agp_message", ""))
    if message.startswith("Infeasible") or "FAIL" in str((status or {}).get("agp_actions", "")):
        return "4_declared_infeasible"
    return "5_other"


def rules_abc(
    *,
    features: Mapping[str, TrajectoryFeatures],
    status1: Mapping[str, Mapping[str, Any] | None],
    status2: Mapping[str, Mapping[str, Any] | None],
    s1: Mapping[str, float],
    s2: Mapping[str, float],
    clean: Sequence[str],
    h_rewards: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    def feat(record: Mapping[str, Any] | None) -> TrajectoryFeatures | None:
        trajectory = (record or {}).get("trajectory_id")
        found = features.get(str(trajectory)) if trajectory else None
        return found if found is not None and found.parsed else None

    episodes = [(t, status1[t]) for t in s1] + [(t, status2[t]) for t in s2]
    joined = sum(1 for _, record in episodes if feat(record) is not None)
    coverage = joined / len(episodes) if episodes else 0.0
    coverage_ok = coverage >= 0.95

    pairs = [(t, feat(status1[t]), feat(status2[t])) for t in clean]
    pairs = [(t, a, b) for t, a, b in pairs if a is not None and b is not None]
    steps1 = np.array([a.steps for _, a, _ in pairs], float)
    steps2 = np.array([b.steps for _, _, b in pairs], float)
    positive = (steps1 > 0) & (steps2 > 0)
    ratio = float(np.median(steps1[positive] / steps2[positive])) if positive.any() else math.nan
    if len(pairs) and np.any(steps1 != steps2):
        p_a = float(stats.wilcoxon(steps1, steps2).pvalue)
    else:
        p_a = 1.0
    rule_a = {
        "n_pairs": len(pairs),
        "median_run1": float(np.median(steps1)) if len(pairs) else None,
        "median_run2": float(np.median(steps2)) if len(pairs) else None,
        "median_ratio_run1_over_run2": ratio,
        "wilcoxon_p": p_a,
        "step_cap_hits": {
            "run1": int(np.sum(steps1 >= STEP_CAP)),
            "run2": int(np.sum(steps2 >= STEP_CAP)),
        },
    }

    # Specificity guard, applied before any unique failure is classified: an
    # environment criterion that fires on more than 20% of the episodes of
    # clean tasks both runs passed cannot diagnose an environment failure and
    # is dropped from class 2 (the classification with it is still reported).
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
        for name in ENV_CRITERIA
        if specificity[name] is not None and specificity[name] <= SPECIFICITY_LIMIT
    )

    def classify(failing_run: str, criteria: Sequence[str] = in_force) -> dict[str, Any]:
        if failing_run == "run2":
            tasks = unique_failures(s2, s1, h_rewards, clean)
            mine_status, other_status = status2, status1
        else:
            tasks = unique_failures(s1, s2, h_rewards, clean)
            mine_status, other_status = status1, status2
        labels = {
            t: failure_signature(
                feat(mine_status[t]), feat(other_status[t]), mine_status[t], criteria
            )
            for t in tasks
        }
        counts = Counter(labels.values())
        n = len(tasks)
        env_share = counts["2_environment"] / n if n else None
        agent_share = (counts["1_step_cap"] + counts["3_premature_answer"]) / n if n else None
        if not n:
            verdict = "no unique failures"
        elif env_share is not None and env_share >= 0.5:
            verdict = "R1-retro: infrastructure"
        elif agent_share is not None and agent_share >= 0.5:
            verdict = "agent-side session variation"
        else:
            verdict = "unexplained"
        return {
            "tasks": n,
            "classes": dict(sorted(counts.items())),
            "environment_share": env_share,
            "step_cap_plus_premature_share": agent_share,
            "verdict": verdict,
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
        "rule_b_run2_unique_failures": classify("run2"),
        "rule_b_run1_unique_failures": classify("run1"),
        "rule_b_run2_all_criteria_sensitivity": classify("run2", ENV_CRITERIA),
    }


# ---- Design power (inputs are already-inspected data only) ---------------- #


def power_rule_d(
    *,
    n_clean: int,
    run1_only: int,
    run2_only: int,
    n_l_values: Sequence[int] = (10, 20, 40, 60),
    r_l_values: Sequence[float] = (0.15, 0.20, 0.30, 0.40),
    alpha: float = 0.025,
    sims: int = 2000,
    seeds: Sequence[int] = (42, 43, 44),
) -> list[dict[str, Any]]:
    """Power of rule (d) given the known clean-set flip totals.

    L tasks pass in run1 only with probability ``r_l``; the remaining run1-only
    passes are spread over the other tasks so the expected total matches the
    observed one; run2-only passes occur at the observed base rate everywhere.
    ``alpha`` is the worst case under Holm with m = 2. A detection needs the
    Fisher test and the 50 % net-share condition together.
    """
    q2 = run2_only / n_clean
    rows = []
    for n_l in n_l_values:
        n_rest = n_clean - n_l
        for r_l in r_l_values:
            r_rest = max(0.0, (run1_only - n_l * r_l) / n_rest)
            per_seed = []
            for seed in seeds:
                rng = np.random.default_rng(seed)
                hits = 0
                for _ in range(sims):
                    a = int(rng.binomial(n_l, r_l))
                    c = int(rng.binomial(n_rest, r_rest))
                    b_l = int(rng.binomial(n_l - a, q2))
                    b_rest = int(rng.binomial(n_rest - c, q2))
                    net_all = (a + c) - (b_l + b_rest)
                    share = (a - b_l) / net_all if net_all > 0 else -1.0
                    if share >= 0.5 and fisher_one_sided([[a, n_l - a], [c, n_rest - c]]) < alpha:
                        hits += 1
                per_seed.append(hits / sims)
            rows.append(
                {
                    "n_L": n_l,
                    "run1_only_rate_in_L": r_l,
                    "run1_only_rate_elsewhere": r_rest,
                    "power_by_seed": dict(zip(map(str, seeds), per_seed, strict=True)),
                    "power_mean": float(np.mean(per_seed)),
                }
            )
    return rows


def power_rule_a(
    base_pairs: Sequence[tuple[int, int]],
    *,
    n: int,
    ratios: Sequence[float] = (1.0, 1.05, 1.10, 1.15, 1.20, 1.30),
    alpha: float = 0.005,
    sims: int = 400,
    seeds: Sequence[int] = (42, 43, 44),
) -> list[dict[str, Any]]:
    """Power of rule (a) by bootstrapping rerun step-count pairs.

    ``base_pairs`` are (steps, steps) for the same task in two reruns that
    share a harness (the H runs). Run2's steps are scaled by ``ratio`` and
    capped at the step cap; a detection needs Wilcoxon p < ``alpha`` (worst case
    under Holm with m = 2 for the 0.01 threshold) and |median ratio - 1| >= 0.10.
    """
    base = np.asarray(base_pairs, float)
    rows = []
    for ratio in ratios:
        per_seed = []
        for seed in seeds:
            rng = np.random.default_rng(seed)
            hits = 0
            for _ in range(sims):
                sample = base[rng.integers(0, len(base), size=n)]
                a = sample[:, 0]
                b = np.minimum(STEP_CAP, np.maximum(1, np.round(sample[:, 1] * ratio)))
                if not np.any(a != b):
                    continue
                p = float(stats.wilcoxon(a, b).pvalue)
                med = float(np.median(a / b))
                if p < alpha and abs(med - 1) >= 0.10:
                    hits += 1
            per_seed.append(hits / sims)
        rows.append(
            {
                "run2_step_ratio": ratio,
                "power_by_seed": dict(zip(map(str, seeds), per_seed, strict=True)),
                "power_mean": float(np.mean(per_seed)),
            }
        )
    return rows


def v2_decisions(rule_d_result: Mapping[str, Any], abc: Mapping[str, Any] | None) -> dict[str, Any]:
    """Holm over (a) and (d), m = 2 always; a test that was not run enters with p = 1."""
    p_d = float(rule_d_result["fisher_one_sided_p"])
    p_a = float(abc["rule_a_steps"]["wilcoxon_p"]) if abc else 1.0
    adj_a, adj_d = holm([p_a, p_d])
    share = rule_d_result["share_of_net_in_L"]
    d_fires = adj_d < 0.05 and share is not None and share >= 0.5
    out: dict[str, Any] = {
        "holm_family": ["a", "d"],
        "p_raw": {"a": p_a, "d": p_d},
        "p_holm": {"a": adj_a, "d": adj_d},
        "rule_d": "checker-side time-drift candidate"
        if d_fires
        else "not attributable to checker time-dependence",
    }
    if abc is None:
        out["rule_a"] = "NOT RUN (trajectory tarball not read)"
        out["rule_b"] = "NOT RUN (trajectory tarball not read)"
        out["rule_c"] = "NOT RUN (trajectory tarball not read)"
        return out
    coverage_ok = abc["rule_c_coverage"]["coverage_ok"]
    ratio = abc["rule_a_steps"]["median_ratio_run1_over_run2"]
    shift = adj_a < 0.01 and math.isfinite(ratio) and abs(ratio - 1) >= 0.10
    out["rule_c"] = (
        "coverage ok" if coverage_ok else "coverage-limited: (a) and (b) descriptive only"
    )
    out["rule_a"] = (
        ("agent-behaviour shift" if shift else "no agent-behaviour shift")
        if coverage_ok
        else "descriptive only (coverage < 95%)"
    )
    out["rule_b"] = (
        abc["rule_b_run2_unique_failures"]["verdict"]
        if coverage_ok
        else "descriptive only (coverage < 95%)"
    )
    return out
