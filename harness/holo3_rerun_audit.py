"""Holo3-35B-A3B rerun audit (Q2 Stage 0c follow-up): data model and statistics.

The OSWorld-Verified leaderboard lists Holo3-35B-A3B twice (82.56 and 78.15).
Both rows are maintainer runs from one package in the public dataset
``xlangai/ubuntu_osworld_verified_trajs``. This module rebuilds the per-task
score matrices of those two runs, of three unlisted H Company runs, and of six
OpenCUA three-run sets, from small byte-range reads of the pinned archives, and
computes the statistics of the v1 post-hoc record and of the v2 registration's
exploratory external reference.

Nothing here downloads a trajectory tarball or screenshots. Every member read
is checked against its zip CRC-32, and every member of the verified package is
also checked against the package's own ``SHA256SUMS``.

Labels: every v1 number is POST-HOC (see
``program/preregistrations/q2-holo3-rerun-audit-v1-posthoc.md``). Every OpenCUA
number is EXPLORATORY (it was inspected during review before any registration).
"""

from __future__ import annotations

import collections
import itertools
import json
import math
import re
import threading
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from harness import remote_zip
from harness.remote_zip import MemberCache, RangeSource, ZipMember

# --------------------------------------------------------------------------- #
# Pinned sources
# --------------------------------------------------------------------------- #

DATASET_REPO = "xlangai/ubuntu_osworld_verified_trajs"
DATASET_REVISION = "5473c39e42a538a187a9b2c2b499db59d560fd8c"
DATASET_LICENSE = "MIT (dataset card cardData.license)"


@dataclass(frozen=True)
class ArchiveSpec:
    key: str
    path: str
    size: int
    lfs_sha256: str


HOLO3_PREFIX = "OSWorldSurfer-Holo3-35B-A3B-20260330-OSWorld-Verified"
VERIFIED_ARCHIVE = ArchiveSpec(
    "holo3-verified",
    f"{HOLO3_PREFIX}_20260420_verified-run_with-local-rewards.zip",
    5_773_773_410,
    "0dea53ac7b04fa7d962c2da48e4c5b4023455c221043378fe1857daf97251ca4",
)
INTERNAL_ARCHIVE = ArchiveSpec(
    "holo3-internal",
    f"{HOLO3_PREFIX}_hcompany-internal-runs-20260416_complete-with-rewards.zip",
    9_127_328_489,
    "9f2c17ae83b605992608386e68c75b284d74217bc3267f2b851b68a2b838ea4c",
)
_OC = "opencua_agent-opencua_{size}-cot_l2-action_history-3image-Ubuntu-{steps}steps.zip"
OPENCUA_ARCHIVES: dict[str, ArchiveSpec] = {
    spec.key: spec
    for spec in (
        ArchiveSpec(
            "opencua-7b-15",
            _OC.format(size="7b", steps=15),
            7_920_092_071,
            "b642e1212d3ebb87e88addc0c55525b12d1ce8b9b253306fa7706908778e9688",
        ),
        ArchiveSpec(
            "opencua-7b-50",
            _OC.format(size="7b", steps=50),
            12_012_284_286,
            "ad9e0a1c5b0fbe1df99f5c0e29f5a48990dc9a4e13505161b87dda558c98504b",
        ),
        ArchiveSpec(
            "opencua-7b-100",
            _OC.format(size="7b", steps=100),
            12_983_641_963,
            "3a0abf7be185a7e9d413a33a4407e06da88ecca0a21eb4dc86470966a70d2669",
        ),
        ArchiveSpec(
            "opencua-32b-15",
            _OC.format(size="32b", steps=15),
            7_763_337_166,
            "7ff9a5edd26353c277a21a291d439f3773e9075ab05bdc2f508c17ac5fdf1781",
        ),
        ArchiveSpec(
            "opencua-32b-50",
            _OC.format(size="32b", steps=50),
            12_100_856_790,
            "fc657378bedc2c411fdfb5622138cef788b381d4de534a26499511f5c47e1973",
        ),
        ArchiveSpec(
            "opencua-32b-100",
            _OC.format(size="32b", steps=100),
            13_053_766_042,
            "38a052a86502bdea76bf0383fd16fb3b767f55e781ff48de66959207927ef6e1",
        ),
    )
}

VERIFIED_ROOT = f"{HOLO3_PREFIX}_20260420_verified-run_with-local-rewards/"
INTERNAL_ROOT = f"{HOLO3_PREFIX}_hcompany-internal-runs-20260416_complete-with-rewards/"
RUN_DIRS = {
    "run1": "local_results/results_hcompany_verified_run1_20260420_121655",
    "repair": "local_results/results_hcompany_verified_run1_repair_20260420_183538",
    "run2": "local_results/results_hcompany_verified_run2_20260420_191308",
}
TARBALL_RELPATH = "trajectories/hcompany_verified_run_20260420_trajectories.tar.gz"
H_RUN_TAGS = ("072452", "072955", "073458")
DOMAINS = (
    "chrome",
    "gimp",
    "libreoffice_calc",
    "libreoffice_impress",
    "libreoffice_writer",
    "multi_apps",
    "os",
    "thunderbird",
    "vlc",
    "vs_code",
)

OSWORLD_REPO = "xlang-ai/OSWorld"
# v1 read the task configs at this commit (latest OSWorld commit before run1).
OSWORLD_V1_CONFIG_COMMIT = "c7e54d24d136d52be0c6d5a7487a1a32f99e7017"
# v2 reads them at PR #477's head; evaluation_examples/ is identical between
# the two commits (git diff of evaluation_examples is empty).
OSWORLD_V2_CONFIG_COMMIT = "f723037959a9d70af4a9f39922ec63ae6f078196"
OSWORLD_LICENSE = "Apache-2.0"

LEADERBOARD_SITE_COMMIT = "62f8466dbe8b4d67c104b5ead3f8271da01aa09d"
LEADERBOARD_URL = (
    "https://raw.githubusercontent.com/OS-World/OS-World.github.io/"
    f"{LEADERBOARD_SITE_COMMIT}/static/data/osworld_verified_results.xlsx"
)
LEADERBOARD_SHA256 = "cf6b4b67eed566ddcd5a8b7ad2d89013157978dad0eea76ea12d2377471efc09"
LEADERBOARD_LICENSE = "none declared (GitHub API license null): numbers cited, file not stored"
LEADERBOARD_DOMAIN_COLUMNS = dict(zip("MNOPQRSTUV", DOMAINS, strict=True))

# Leaderboard cells (Success/Total and per-domain), transcribed from the sheet
# above and re-checked against it by ``check_leaderboard_constants``.
HOLO3_LEADERBOARD: dict[str, dict[str, Any]] = {
    "run1": {
        "row": 139,
        "total": "296.41/359",
        "cells": {
            "chrome": "36.96/44",
            "gimp": "23.00/26",
            "libreoffice_calc": "40.00/47",
            "libreoffice_impress": "41.55/47",
            "libreoffice_writer": "18.97/23",
            "multi_apps": "60.94/93",
            "os": "23.00/24",
            "thunderbird": "14.00/15",
            "vlc": "15.99/17",
            "vs_code": "22.00/23",
        },
    },
    "run2": {
        "row": 140,
        "total": "280.55/359",
        "cells": {
            "chrome": "31.96/44",
            "gimp": "23.00/26",
            "libreoffice_calc": "38.00/47",
            "libreoffice_impress": "36.55/47",
            "libreoffice_writer": "19.97/23",
            "multi_apps": "56.09/93",
            "os": "23.00/24",
            "thunderbird": "14.00/15",
            "vlc": "15.99/17",
            "vs_code": "22.00/23",
        },
    },
}
OPENCUA_LEADERBOARD: dict[str, dict[int, str]] = {
    "opencua-7b-15": {36: "93.95/359", 37: "86.08/360", 38: "82.72/360"},
    "opencua-7b-50": {39: "104.14/361", 40: "99.05/357", 41: "100.25/358"},
    "opencua-7b-100": {42: "97.57/359", 43: "94.08/361", 44: "95.65/360"},
    "opencua-32b-15": {45: "100.42/357", 46: "109.80/360", 47: "109.34/360"},
    "opencua-32b-50": {48: "121.57/360", 49: "120.31/359", 50: "126.49/360"},
    "opencua-32b-100": {51: "121.83/360", 52: "125.22/360", 53: "127.95/358"},
}
OPENCUA_MODEL_NAMES = {"7b": "opencua-7b", "32b": "opencua-32b"}

# Numbers the v1 analysis printed on the host (analysis/run_output.txt,
# sha256 a24e1590...). The doctor must reproduce them from scratch. Strings
# are the exact printed formats.
V1_RECORDED: dict[str, Any] = {
    "scored": {"run1": 359, "run2": 359},
    "sum": {"run1": "296.4052", "run2": "280.5495"},
    "passed_gt0": {"run1": 298, "run2": 282},
    "common": 359,
    "infra_flagged": 17,
    "clean": 342,
    "web_tasks": 53,
    "mcnemar": {
        "ge": {"C": [25, 9, "0.009041"], "clean": [23, 9, "0.02006"]},
        "gt0": {"C": [25, 9, "0.009041"], "clean": [23, 9, "0.02006"]},
        "eq1": {"C": [24, 10, "0.02431"], "clean": [22, 10, "0.0501"]},
    },
    "sign_flip_p": {"C": "0.008744", "clean": "0.01902"},
    "gap_pp": "4.417",
    "inclusion_pp": "0.000",
    "components_tasks": {
        "infra_flagged": "+2.000",
        "web_clean": "+6.908",
        "offline_clean": "+6.948",
    },
    "components_pp": {"infra_flagged": "+0.557", "web_clean": "+1.924", "offline_clean": "+1.935"},
    "web_strata": {"web": [48, 7, 0, "0.0156"], "offline": [294, 16, 9, "0.23"]},
    "elapsed": {"median_run1": "97.1", "median_run2": "107.8", "ratio": "0.997", "p": "0.51"},
    "h_sums": {"072452": "286.0276", "072955": "285.1064", "073458": "285.6962"},
    "h_pairs": [[32, "0.0899", 0], [37, "0.1039", 1], [37, "0.1042", 1]],
    "q_h": "0.0993",
    "sd_pp": "1.664",
    "gap_in_sd": "2.65",
    "h_model_p": "0.1025",
}

# --------------------------------------------------------------------------- #
# Public-repository safety
# --------------------------------------------------------------------------- #

PUBLIC_UNSAFE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # A trailing sentence period is allowed; a fifth dotted group is not.
    ("ipv4", re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?!\w|\.\d)")),
    ("aws_private_dns", re.compile(r"\bip-\d{1,3}(?:-\d{1,3}){3}\b")),
    ("aws_security_group", re.compile(r"\bsg-[0-9a-f]{8,17}\b")),
    ("aws_subnet", re.compile(r"\bsubnet-[0-9a-f]{8,17}\b")),
    ("aws_vpc", re.compile(r"\bvpc-[0-9a-f]{8,17}\b")),
    ("aws_ami", re.compile(r"\bami-[0-9a-f]{8,17}\b")),
    ("aws_instance", re.compile(r"\bi-[0-9a-f]{8,17}\b")),
    # 12-digit AWS account id; anchored so UUID segments and long decimals do
    # not match (UUID groups are preceded by '-', decimals by '.').
    ("aws_account_id", re.compile(r"(?<![\w.\-])\d{12}(?![\w\-])")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("home_path", re.compile(r"/(?:home|Users)/[^/\s\"']+")),
    ("shared_fs_path", re.compile(r"(?:^|[\s\"'/])fsx/[^/\s\"']+")),
    ("websocket_url", re.compile(r"\bwss?://")),
    ("cdp_browser_id", re.compile(r"devtools/browser/")),
    ("signed_url", re.compile(r"(?:X-Amz-Signature|Signature=|Key-Pair-Id=|Policy=)")),
    ("api_token", re.compile(r"\b(?:hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_\-]{20,})\b")),
)


class PublicSafetyError(ValueError):
    """A value bound for a public receipt matched a forbidden pattern."""


def public_safety_hits(text: str) -> list[str]:
    return [name for name, pattern in PUBLIC_UNSAFE_PATTERNS if pattern.search(text)]


def scrub(text: str) -> str:
    for name, pattern in PUBLIC_UNSAFE_PATTERNS:
        text = pattern.sub(f"[redacted-{name}]", text)
    return text


def assert_public_safe(obj: Any, where: str = "receipt") -> None:
    """Fail closed if any key, string or number matches a forbidden pattern.

    The error names the patterns and JSON paths, never the matched text.
    """
    hits: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                for name in public_safety_hits(str(key)):
                    hits.append(f"{path}.<key>:{name}")
                walk(item, f"{path}.{key}")
        elif isinstance(value, list | tuple):
            for index, item in enumerate(value):
                walk(item, f"{path}[{index}]")
        elif isinstance(value, str):
            for name in public_safety_hits(value):
                hits.append(f"{path}:{name}")
        elif isinstance(value, int | float) and not isinstance(value, bool):
            # A 12-digit account id or a packed address can arrive as a number.
            for name in public_safety_hits(str(value)):
                hits.append(f"{path}:{name}")

    walk(obj, where)
    if hits:
        raise PublicSafetyError(f"{len(hits)} public-safety hits: {sorted(set(hits))[:10]}")


def error_class(text: str | None) -> str:
    """Coarse, public-safe class of a runner error string."""
    if not text:
        return "none"
    if "connect_over_cdp" in text and "Timeout" in text:
        return "setup_cdp_timeout"
    if "month must be in 1..12" in text:
        return "evaluator_month_out_of_range"
    if "Flask not available" in text:
        return "vm_flask_unavailable"
    return "other"


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #

Scores = Mapping[str, float]
BINARIZE: dict[str, Callable[[float], bool]] = {
    "ge": lambda x: x >= 0.5,
    "gt0": lambda x: x > 0,
    "eq1": lambda x: x == 1.0,
}


@dataclass(frozen=True)
class McNemar:
    n10: int
    n01: int
    n: int
    p: float

    @property
    def discordant(self) -> int:
        return self.n10 + self.n01

    @property
    def z(self) -> float:
        k = self.discordant
        return (self.n10 - self.n01) / math.sqrt(k) if k else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "a_only": self.n10,
            "b_only": self.n01,
            "discordant": self.discordant,
            "discordance_rate": self.discordant / self.n if self.n else None,
            "exact_p": self.p,
            "z": self.z,
        }


def mcnemar(tasks: Sequence[str], a: Scores, b: Scores, mode: str = "ge") -> McNemar:
    """Exact two-sided McNemar (binomial on discordant pairs, p = 0.5)."""
    y = BINARIZE[mode]
    n10 = sum(1 for t in tasks if y(a[t]) and not y(b[t]))
    n01 = sum(1 for t in tasks if not y(a[t]) and y(b[t]))
    k = n10 + n01
    p = float(stats.binomtest(n10, k, 0.5).pvalue) if k else 1.0
    return McNemar(n10, n01, len(tasks), p)


def holm(pvalues: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values, in input order."""
    order = np.argsort(pvalues, kind="stable")
    m = len(pvalues)
    adjusted = [0.0] * m
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[index]))
        adjusted[index] = running
    return adjusted


def clopper_pearson(k: int, n: int) -> tuple[float, float]:
    ci = stats.binomtest(k, n).proportion_ci(0.95, method="exact")
    return float(ci.low), float(ci.high)


def sign_flip_p(
    diffs: Sequence[float],
    rng: np.random.Generator,
    draws: int = 1_000_000,
    chunk_rows: int = 50_000,
) -> float:
    """Monte Carlo paired sign-flip test on the sum of differences.

    Draws are made in row chunks; for numpy's Generator this reproduces the
    stream of a single ``choice`` call of the full size (tested), so v1's
    one-shot numbers are reproduced with bounded memory.
    """
    d = np.asarray(diffs, dtype=float)
    nonzero = np.abs(d[d != 0])
    observed = abs(float(d.sum()))
    hits = 0
    done = 0
    while done < draws:
        rows = min(chunk_rows, draws - done)
        signs = rng.choice([-1.0, 1.0], size=(rows, nonzero.size))
        sims = (signs * nonzero).sum(1)
        hits += int(np.count_nonzero(np.abs(sims) >= observed - 1e-12))
        done += rows
    return hits / draws


def two_way_variance_ratio(matrix: np.ndarray) -> dict[str, float]:
    """Between-run vs residual mean squares for a tasks x runs 0/1 matrix.

    Under exchangeable reruns (no run effect) the ratio has expectation about
    1 and is distributed F(R-1, (n-1)(R-1)).
    """
    n, r = matrix.shape
    grand = matrix.mean()
    run_means = matrix.mean(0)
    task_means = matrix.mean(1)
    ss_runs = n * float(((run_means - grand) ** 2).sum())
    resid = matrix - task_means[:, None] - run_means[None, :] + grand
    ss_resid = float((resid**2).sum())
    return {
        "n_tasks": n,
        "n_runs": r,
        "ss_runs": ss_runs,
        "df_runs": r - 1,
        "ss_resid": ss_resid,
        "df_resid": (n - 1) * (r - 1),
    }


def pooled_variance_ratio(parts: Iterable[Mapping[str, float]]) -> dict[str, float]:
    parts = list(parts)
    ss_runs = sum(p["ss_runs"] for p in parts)
    df_runs = sum(p["df_runs"] for p in parts)
    ss_resid = sum(p["ss_resid"] for p in parts)
    df_resid = sum(p["df_resid"] for p in parts)
    ratio = (ss_runs / df_runs) / (ss_resid / df_resid) if df_runs and ss_resid else float("nan")
    p_upper = float(stats.f.sf(ratio, df_runs, df_resid)) if math.isfinite(ratio) else float("nan")
    return {"ratio": ratio, "df_runs": df_runs, "df_resid": df_resid, "p_upper": p_upper}


def mde_two_run_contrast(q: float, n: int, alpha: float = 0.05, power: float = 0.8) -> float:
    """Minimum detectable two-run gap (proportion) from a discordance rate q."""
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return float(z * math.sqrt(q / n))


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #

SourceOpener = Callable[[ArchiveSpec], RangeSource]


@dataclass
class FetchContext:
    """Opens pinned archives and remembers what was read for the receipt."""

    open_archive: SourceOpener
    cache: MemberCache | None = None
    max_workers: int = remote_zip.MAX_CONCURRENCY
    _sources: dict[str, RangeSource] = field(default_factory=dict)
    _listings: dict[str, list[ZipMember]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    members_read: dict[str, int] = field(default_factory=dict)

    def source(self, spec: ArchiveSpec) -> RangeSource:
        with self._lock:
            if spec.key not in self._sources:
                self._sources[spec.key] = self.open_archive(spec)
            return self._sources[spec.key]

    def listing(self, spec: ArchiveSpec) -> list[ZipMember]:
        if spec.key not in self._listings:
            self._listings[spec.key] = remote_zip.list_members(self.source(spec))
        return self._listings[spec.key]

    def extract(
        self,
        source: RangeSource,
        namespace: str,
        members: Sequence[ZipMember],
        uncached: Callable[[ZipMember], bool] = lambda m: False,
    ) -> dict[str, bytes]:
        out = remote_zip.extract_members(
            source,
            members,
            cache=self.cache,
            namespace=namespace,
            uncached=uncached,
            max_workers=self.max_workers,
        )
        self.members_read[namespace] = self.members_read.get(namespace, 0) + len(out)
        return out

    def identities(self) -> dict[str, Any]:
        return {key: src.identity() for key, src in sorted(self._sources.items())}


def _digest_manifest(entries: Mapping[str, str]) -> str:
    payload = json.dumps(sorted(entries.items()), separators=(",", ":")).encode()
    return remote_zip.sha256_bytes(payload)


# --------------------------------------------------------------------------- #
# Verified package (run1, repair, run2)
# --------------------------------------------------------------------------- #

LOG_LINE = re.compile(r"\]\[([0-9a-f]{8})\] (.*)")


@dataclass
class VerifiedPackage:
    universe: list[tuple[str, str]]
    repair_tasks: list[str]
    status: dict[str, dict[str, dict[str, Any]]]
    result_txt: dict[str, dict[str, str]]
    env_prep_failures: dict[str, collections.Counter[str]]
    agp_done_counts: dict[str, collections.Counter[str]]
    summaries: dict[str, dict[str, Any]]
    sha256sums: dict[str, str]
    member_sha256: dict[str, str]
    tarball: dict[str, Any]

    @property
    def tasks(self) -> list[str]:
        return [t for _, t in self.universe]

    @property
    def domain_of(self) -> dict[str, str]:
        return {t: d for d, t in self.universe}


def parse_sha256sums(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        digest, path = line.split(None, 1)
        path = path.strip().lstrip("*")
        path = path[2:] if path.startswith("./") else path
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise remote_zip.ZipIntegrityError("SHA256SUMS has a malformed digest line")
        out[path] = digest
    return out


def parse_env_prep_log(data: bytes) -> tuple[collections.Counter[str], collections.Counter[str]]:
    """Count env-prep failures and AGP completions per 8-hex task prefix.

    The log is parsed in memory only; only prefixes and counts leave here.
    """
    env_prep: collections.Counter[str] = collections.Counter()
    agp_done: collections.Counter[str] = collections.Counter()
    for raw_line in data.decode("utf-8", errors="replace").splitlines():
        if "surferH.benchmark_retry" not in raw_line:
            continue
        match = LOG_LINE.search(raw_line)
        if not match:
            continue
        prefix, message = match.groups()
        if message.startswith("Env prep failed"):
            env_prep[prefix] += 1
        if message.startswith("AGP done"):
            agp_done[prefix] += 1
    return env_prep, agp_done


def _status_path(run_dir: str, domain: str, task: str) -> str:
    return f"{run_dir}/pyautogui/screenshot/{HOLO3_PREFIX}/{domain}/{task}/status.json"


def load_verified_package(ctx: FetchContext) -> VerifiedPackage:
    spec = VERIFIED_ARCHIVE
    source = ctx.source(spec)
    members = ctx.listing(spec)
    by_rel = {m.name[len(VERIFIED_ROOT) :]: m for m in members if m.name.startswith(VERIFIED_ROOT)}
    if len(by_rel) != len(members):
        raise remote_zip.ZipIntegrityError("verified package has members outside its root")
    run_prefixes = {
        key: f"{path}/pyautogui/screenshot/{HOLO3_PREFIX}/" for key, path in RUN_DIRS.items()
    }
    wanted = [
        "SHA256SUMS",
        "evaluation_examples/test_nogdrive.json",
        "evaluation_examples/test_hcompany_run1_repair.json",
        f"{RUN_DIRS['run1']}/merged_summary_with_repair.json",
        f"{RUN_DIRS['run2']}/final_summary.json",
        *(f"{path}/benchmark.log" for path in RUN_DIRS.values()),
    ]
    for rel, member in by_rel.items():
        if member.is_dir:
            continue
        if any(rel.startswith(p) for p in run_prefixes.values()) and rel.endswith(
            ("/status.json", "/result.txt")
        ):
            wanted.append(rel)
    chosen = remote_zip.select(members, [VERIFIED_ROOT + rel for rel in wanted])
    data = ctx.extract(
        source,
        spec.lfs_sha256,
        chosen,
        uncached=lambda m: m.name.endswith("benchmark.log"),
    )
    files = {name[len(VERIFIED_ROOT) :]: blob for name, blob in data.items()}
    sums = parse_sha256sums(files["SHA256SUMS"].decode())
    member_sha: dict[str, str] = {}
    for rel, blob in files.items():
        if rel == "SHA256SUMS":
            continue
        digest = remote_zip.sha256_bytes(blob)
        if sums.get(rel) != digest:
            raise remote_zip.ZipIntegrityError(f"SHA256SUMS mismatch or missing entry for {rel}")
        member_sha[rel] = digest

    universe_raw = json.loads(files["evaluation_examples/test_nogdrive.json"])
    universe = [(d, t) for d, ts in universe_raw.items() for t in ts]
    if len({t for _, t in universe}) != len(universe):
        raise remote_zip.ZipIntegrityError("task universe has duplicate task ids")
    repair_raw = json.loads(files["evaluation_examples/test_hcompany_run1_repair.json"])
    repair_tasks = [t for ts in repair_raw.values() for t in ts]
    domain_of = {t: d for d, t in universe}

    status: dict[str, dict[str, dict[str, Any]]] = {key: {} for key in RUN_DIRS}
    result_txt: dict[str, dict[str, str]] = {key: {} for key in RUN_DIRS}
    for rel, blob in files.items():
        for key, prefix in run_prefixes.items():
            if not rel.startswith(prefix):
                continue
            parts = rel[len(prefix) :].split("/")
            if len(parts) != 3:
                raise remote_zip.ZipIntegrityError(f"unexpected per-task path depth: {rel}")
            domain, task, leaf = parts
            if domain_of.get(task) != domain:
                raise remote_zip.ZipIntegrityError(f"task {task} not in universe under {domain}")
            if leaf == "status.json":
                record = json.loads(blob)
                if record.get("task_id") != task:
                    raise remote_zip.ZipIntegrityError(f"status.json task_id mismatch for {task}")
                status[key][task] = record
            else:
                result_txt[key][task] = blob.decode().strip()

    env_prep: dict[str, collections.Counter[str]] = {}
    agp_done: dict[str, collections.Counter[str]] = {}
    for key, path in RUN_DIRS.items():
        env_prep[key], agp_done[key] = parse_env_prep_log(files[f"{path}/benchmark.log"])

    merged = json.loads(files[f"{RUN_DIRS['run1']}/merged_summary_with_repair.json"])
    final = json.loads(files[f"{RUN_DIRS['run2']}/final_summary.json"])
    numeric = ("total_tasks", "scored", "passed", "errors", "score")
    summaries = {
        "run1_merged_with_repair": {k: merged.get(k) for k in numeric},
        "run2_final": {k: final.get(k) for k in numeric},
    }
    tar_member = by_rel[TARBALL_RELPATH]
    tarball = {
        "relpath": TARBALL_RELPATH,
        "size": tar_member.file_size,
        "crc32": f"{tar_member.crc:08x}",
        "header_offset": tar_member.header_offset,
        "compress_type": tar_member.compress_type,
        "sha256_from_sha256sums": sums.get(TARBALL_RELPATH),
    }
    return VerifiedPackage(
        universe=universe,
        repair_tasks=repair_tasks,
        status=status,
        result_txt=result_txt,
        env_prep_failures=env_prep,
        agp_done_counts=agp_done,
        summaries=summaries,
        sha256sums=sums,
        member_sha256=member_sha,
        tarball=tarball,
    )


# --------------------------------------------------------------------------- #
# H Company internal runs (nested stored zips)
# --------------------------------------------------------------------------- #


@dataclass
class HRuns:
    rewards: dict[str, dict[str, float]]
    null_rewards: dict[str, list[str]]
    err_files: dict[str, list[str]]
    steps: dict[str, dict[str, int]]
    member_sha256: dict[str, str]
    nested: dict[str, dict[str, Any]]
    features: dict[str, dict[str, Any]] = field(default_factory=dict)


def load_h_runs(
    ctx: FetchContext,
    universe: Sequence[tuple[str, str]],
    with_steps: bool,
    on_actions: Callable[[str, str, Any], None] | None = None,
) -> HRuns:
    """Rewards (and, with ``with_steps``, step counts) of the three H Company runs.

    ``on_actions(tag, task, entries)`` sees each parsed actions.json in memory;
    it is how the v2 design calibrates its failure signatures on these runs.
    """
    spec = INTERNAL_ARCHIVE
    source = ctx.source(spec)
    outer = ctx.listing(spec)
    domain_of = {t: d for d, t in universe}
    rewards: dict[str, dict[str, float]] = {}
    nulls: dict[str, list[str]] = {}
    errs: dict[str, list[str]] = {}
    steps: dict[str, dict[str, int]] = {}
    member_sha: dict[str, str] = {}
    nested_info: dict[str, dict[str, Any]] = {}
    for tag in H_RUN_TAGS:
        name = f"{INTERNAL_ROOT}h_company_internal_runs/trajectories_results_20260416_{tag}.zip"
        (outer_member,) = remote_zip.select(outer, [name])
        window = remote_zip.stored_member_window(source, outer_member)
        inner = remote_zip.list_members(window)
        root = f"trajectories/results_20260416_{tag}/"
        leaves = ["task_summary.json"] + (["actions.json"] if with_steps else [])
        chosen = [
            m
            for m in inner
            if m.name.startswith(root) and not m.is_dir and m.name.rsplit("/", 1)[-1] in leaves
        ]
        errs[tag] = sorted(
            m.name[len(root) :] for m in inner if m.name.endswith(".err") and not m.is_dir
        )
        namespace = f"{spec.lfs_sha256}:{tag}"
        data = ctx.extract(window, namespace, chosen)
        rewards[tag], nulls[tag], steps[tag] = {}, [], {}
        for member_name, blob in data.items():
            parts = member_name[len(root) :].split("/")
            if len(parts) != 3:
                raise remote_zip.ZipIntegrityError(f"unexpected inner path depth: {member_name}")
            domain, task, leaf = parts
            if domain_of.get(task) != domain:
                raise remote_zip.ZipIntegrityError(f"H task {task} not in universe under {domain}")
            member_sha[f"{tag}/{domain}/{task}/{leaf}"] = remote_zip.sha256_bytes(blob)
            payload = json.loads(blob)
            if leaf == "task_summary.json":
                reward = payload.get("reward")
                if reward is None:
                    nulls[tag].append(f"{domain}/{task}")
                else:
                    rewards[tag][task] = float(reward)
            else:
                steps[tag][task] = sum(1 for entry in payload if "action" in entry)
                if on_actions is not None:
                    on_actions(tag, task, payload)
        nulls[tag].sort()
        nested_info[tag] = {
            "outer_member": name[len(INTERNAL_ROOT) :],
            "outer_crc32": f"{outer_member.crc:08x}",
            "size": outer_member.file_size,
            "inner_entries": len(inner),
            "members_read": len(data),
        }
    return HRuns(rewards, nulls, errs, steps, member_sha, nested_info)


# --------------------------------------------------------------------------- #
# OpenCUA three-run sets (EXPLORATORY reference)
# --------------------------------------------------------------------------- #

OPENCUA_RESULT = re.compile(r"^turn_([123])/([a-z_]+)/([0-9a-f-]{36})/result\.txt$")


@dataclass
class OpenCUASet:
    key: str
    turns: dict[str, dict[str, float]]
    domain_of: dict[str, str]
    member_manifest_sha256: str
    members_read: int


def load_opencua(ctx: FetchContext, spec: ArchiveSpec) -> OpenCUASet:
    source = ctx.source(spec)
    members = ctx.listing(spec)
    chosen = [m for m in members if OPENCUA_RESULT.match(m.name)]
    if len(chosen) < 1000:
        raise remote_zip.MissingMemberError(f"{spec.key}: only {len(chosen)} result.txt members")
    data = ctx.extract(source, spec.lfs_sha256, chosen)
    turns: dict[str, dict[str, float]] = collections.defaultdict(dict)
    domain_of: dict[str, str] = {}
    manifest: dict[str, str] = {}
    for name, blob in data.items():
        match = OPENCUA_RESULT.match(name)
        assert match is not None
        turn, domain, task = match.groups()
        if domain not in DOMAINS:
            raise remote_zip.ZipIntegrityError(f"{spec.key}: unknown domain {domain}")
        if domain_of.setdefault(task, domain) != domain:
            raise remote_zip.ZipIntegrityError(f"{spec.key}: task {task} in two domains")
        turns[f"turn_{turn}"][task] = float(blob.decode().strip())
        manifest[name] = remote_zip.sha256_bytes(blob)
    return OpenCUASet(
        key=spec.key,
        turns=dict(sorted(turns.items())),
        domain_of=domain_of,
        member_manifest_sha256=_digest_manifest(manifest),
        members_read=len(data),
    )


# --------------------------------------------------------------------------- #
# Leaderboard checks
# --------------------------------------------------------------------------- #


def cell(total: float, n: int) -> str:
    return f"{total:.2f}/{n}"


def _cell_value(text: str) -> tuple[float, int]:
    value, count = text.split("/")
    return float(value), int(count)


def domain_cells(scores: Scores, domain_of: Mapping[str, str]) -> dict[str, str]:
    sums: dict[str, float] = collections.defaultdict(float)
    counts: collections.Counter[str] = collections.Counter()
    for task, value in scores.items():
        sums[domain_of[task]] += value
        counts[domain_of[task]] += 1
    return {d: cell(sums[d], counts[d]) for d in DOMAINS if counts[d]}


def check_leaderboard_constants(rows: Mapping[int, Mapping[str, str]]) -> dict[str, Any]:
    """Compare the transcribed constants with the pinned leaderboard sheet."""
    problems: list[str] = []
    for run, spec in HOLO3_LEADERBOARD.items():
        row = rows.get(spec["row"], {})
        if row.get("A") != "Holo3-35B-A3B" or row.get("F") != "100":
            problems.append(f"{run}: row {spec['row']} is not Holo3-35B-A3B at 100 steps")
        if row.get("L") != spec["total"]:
            problems.append(f"{run}: total {row.get('L')} != {spec['total']}")
        for column, domain in LEADERBOARD_DOMAIN_COLUMNS.items():
            if row.get(column) != spec["cells"][domain]:
                problems.append(f"{run}: {domain} {row.get(column)} != {spec['cells'][domain]}")
    for key, expected in OPENCUA_LEADERBOARD.items():
        _, size, steps = key.split("-")
        for number, total in expected.items():
            row = rows.get(number, {})
            if row.get("A") != OPENCUA_MODEL_NAMES[size] or row.get("F") != steps:
                problems.append(f"{key}: row {number} is {row.get('A')} at {row.get('F')} steps")
            if row.get("L") != total:
                problems.append(f"{key}: row {number} total {row.get('L')} != {total}")
    return {"status": "PASS" if not problems else "FAIL", "problems": problems}


def rank_by_group_mean(rows: Mapping[int, Mapping[str, str]], model: str, steps: str) -> dict:
    """The site groups rows by model and max steps and sorts by mean success rate."""
    groups: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    for number, row in rows.items():
        if number == 1 or not row.get("A"):
            continue
        try:
            rate = float(row["K"])
        except (KeyError, ValueError):
            continue
        groups[(row["A"], row.get("F", ""))].append(rate)
    ordered = sorted(groups.items(), key=lambda item: -float(np.mean(item[1])))
    for position, (key, values) in enumerate(ordered, 1):
        if key == (model, steps):
            return {
                "rank": position,
                "groups": len(ordered),
                "mean": float(np.mean(values)),
                "population_std": float(np.std(values)),
                "runs": len(values),
            }
    return {"rank": None, "groups": len(ordered)}


# --------------------------------------------------------------------------- #
# v1 matrix and analysis (POST-HOC)
# --------------------------------------------------------------------------- #

ALLOWED_URL = re.compile(
    r"https?://(localhost|127\.0\.0\.1|huggingface\.co/datasets/xlangai/ubuntu_osworld_file_cache)"
)
URL = re.compile(r"https?://[^\s\"']+")


def web_dependent(config: Mapping[str, Any]) -> bool:
    """v1's web flag: a non-local, non-file-cache URL in config or evaluator."""
    blob = json.dumps({"config": config.get("config"), "evaluator": config.get("evaluator")})
    return any(not ALLOWED_URL.match(url) for url in URL.findall(blob))


def _score(record: Mapping[str, Any] | None) -> float | None:
    if record and record.get("status") == "completed":
        return float(record["score"])
    return None


@dataclass
class V1Matrix:
    tasks: list[str]
    domain_of: dict[str, str]
    v1: dict[str, dict[str, Any] | None]
    v1_source: dict[str, str]
    v2: dict[str, dict[str, Any] | None]
    s1: dict[str, float | None]
    s2: dict[str, float | None]
    flags: dict[str, tuple[frozenset[str], frozenset[str]]]
    web: dict[str, bool]


def build_v1_matrix(pkg: VerifiedPackage, web: Mapping[str, bool]) -> V1Matrix:
    tasks = pkg.tasks
    r1, rep, r2 = pkg.status["run1"], pkg.status["repair"], pkg.status["run2"]
    v1: dict[str, dict[str, Any] | None] = {}
    source: dict[str, str] = {}
    for t in tasks:
        a, b = r1.get(t), rep.get(t)
        if a and a.get("status") == "completed":
            v1[t], source[t] = a, "main"
        elif b and b.get("status") == "completed":
            v1[t], source[t] = b, "repair"
        elif a or b:
            v1[t], source[t] = (b or a), "error"
        else:
            v1[t], source[t] = None, "missing"
    v2 = {t: r2.get(t) for t in tasks}
    prefixes = collections.Counter(t[:8] for t in tasks)
    if max(prefixes.values()) != 1:
        raise ValueError("8-character task-id prefixes collide; log flags would be ambiguous")
    f2_run1 = dict(pkg.env_prep_failures["run1"])
    for prefix, count in pkg.env_prep_failures["repair"].items():
        f2_run1[prefix] = f2_run1.get(prefix, 0) + count
    f2_run2 = dict(pkg.env_prep_failures["run2"])

    def flags(t: str, record: Mapping[str, Any] | None, f2: Mapping[str, int]) -> set[str]:
        out: set[str] = set()
        if record is None or record.get("status") != "completed":
            out.add("F1")
        if f2.get(t[:8], 0) > 0:
            out.add("F2")
        if record and str(record.get("agp_message", "")).startswith("Failed"):
            out.add("F3")
        if record and record.get("status") == "completed":
            elapsed = float(record.get("elapsed_s", 0))
            if elapsed >= 10000 or (elapsed < 20 and float(record["score"]) == 0):
                out.add("F4")
        return out

    all_flags: dict[str, tuple[frozenset[str], frozenset[str]]] = {}
    for t in tasks:
        a = flags(t, v1[t], f2_run1)
        if source[t] == "repair":
            a.add("F6")
        b = flags(t, v2[t], f2_run2)
        all_flags[t] = (frozenset(a), frozenset(b))
    missing_web = [t for t in tasks if t not in web]
    if missing_web:
        raise ValueError(f"{len(missing_web)} tasks have no web flag")
    return V1Matrix(
        tasks=tasks,
        domain_of=pkg.domain_of,
        v1=v1,
        v1_source=source,
        v2=v2,
        s1={t: _score(v1[t]) for t in tasks},
        s2={t: _score(v2[t]) for t in tasks},
        flags=all_flags,
        web=dict(web),
    )


def analyze_v1(
    m: V1Matrix,
    h: HRuns,
    *,
    seed: int = 42,
    sign_flip_draws: int = 1_000_000,
    model_draws: int = 100_000,
) -> dict[str, Any]:
    """The v1 analysis, ported line by line from the host script.

    One generator is shared across the sign-flip tests and the H-only model,
    in v1's order, so seed 42 reproduces v1's Monte Carlo numbers.
    """
    T = m.tasks
    s1 = {t: v for t, v in m.s1.items() if v is not None}
    s2 = {t: v for t, v in m.s2.items() if v is not None}
    out: dict[str, Any] = {"seed": seed}
    out["runs"] = {
        name: {
            "scored": len(s),
            "sum": sum(s.values()),
            "rate_pct": 100 * sum(s.values()) / len(s),
            "passed_gt0": sum(1 for x in s.values() if x > 0),
        }
        for name, s in (("run1", s1), ("run2", s2))
    }
    out["run1_sources"] = dict(collections.Counter(m.v1_source.values()))
    errors: dict[str, dict[str, str]] = {}
    for name, records in (("run1", m.v1), ("run2", m.v2)):
        for t in T:
            record = records[t]
            if record and record.get("status") == "error":
                errors.setdefault(name, {})[t] = error_class(str(record.get("error", "")))
    out["errors"] = errors

    C = [t for t in T if t in s1 and t in s2]
    infra = {t for t in C if (m.flags[t][0] | m.flags[t][1]) - {"F1"}}
    clean = [t for t in C if t not in infra]
    out["sets"] = {"common": len(C), "infra_flagged": len(infra), "clean": len(clean)}
    out["infra_flags"] = {
        t: {"run1": sorted(m.flags[t][0]), "run2": sorted(m.flags[t][1])} for t in sorted(infra)
    }
    out["mcnemar"] = {
        mode: {
            name: mcnemar(ts, s1, s2, mode).as_dict() for name, ts in (("C", C), ("clean", clean))
        }
        for mode in ("ge", "gt0", "eq1")
    }

    rng = np.random.default_rng(seed)
    out["sign_flip"] = {}
    for name, ts in (("C", C), ("clean", clean)):
        diffs = [s1[t] - s2[t] for t in ts]
        out["sign_flip"][name] = {
            "sum_d": float(np.sum(diffs)),
            "nonzero": int(np.count_nonzero(diffs)),
            "p": sign_flip_p(diffs, rng, draws=sign_flip_draws),
            "draws": sign_flip_draws,
        }
    fractional = [t for t in C if (0 < s1[t] < 1) or (0 < s2[t] < 1)]
    out["fractional"] = {"tasks": len(fractional), "sum_d": sum(s1[t] - s2[t] for t in fractional)}

    lb1 = sum(s1.values()) / len(s1)
    lb2 = sum(s2.values()) / len(s2)
    gap_pp = 100 * (lb1 - lb2)
    n_c = len(C)
    common_gap_pp = 100 * (sum(s1[t] for t in C) - sum(s2[t] for t in C)) / n_c
    components = {
        "infra_flagged": sum(s1[t] - s2[t] for t in infra),
        "web_clean": sum(s1[t] - s2[t] for t in clean if m.web[t]),
        "offline_clean": sum(s1[t] - s2[t] for t in clean if not m.web[t]),
    }
    inclusion_pp = gap_pp - common_gap_pp
    infra_share = (inclusion_pp + 100 * components["infra_flagged"] / n_c) / gap_pp
    out["decomposition"] = {
        "gap_pp": gap_pp,
        "common_gap_pp": common_gap_pp,
        "inclusion_pp": inclusion_pp,
        "components_tasks": components,
        "components_pp": {k: 100 * v / n_c for k, v in components.items()},
        "infra_share": infra_share,
    }
    out["repaired"] = {
        t: {"domain": m.domain_of[t], "run1": m.s1[t], "run2": m.s2[t]}
        for t in T
        if m.v1_source[t] == "repair"
    }
    out["web_tasks"] = sum(1 for t in T if m.web[t])

    domain_rows = []
    pvalues = []
    for domain in DOMAINS:
        ts = [t for t in clean if m.domain_of[t] == domain]
        test = mcnemar(ts, s1, s2)
        domain_rows.append((domain, test, sum(s1[t] - s2[t] for t in ts)))
        pvalues.append(test.p)
    adjusted = holm(pvalues)
    out["domains_clean"] = {
        domain: {**test.as_dict(), "sum_d": sum_d, "holm_p": adj}
        for (domain, test, sum_d), adj in zip(domain_rows, adjusted, strict=True)
    }
    out["web_strata_clean"] = {
        label: mcnemar([t for t in clean if m.web[t] == flag], s1, s2).as_dict()
        for label, flag in (("web", True), ("offline", False))
    }

    e1 = np.array([float(m.v1[t]["elapsed_s"]) for t in clean])  # type: ignore[index]
    e2 = np.array([float(m.v2[t]["elapsed_s"]) for t in clean])  # type: ignore[index]
    wil = stats.wilcoxon(e1, e2)
    ratio = float(np.median(e1 / e2))
    out["elapsed_clean"] = {
        "median_run1": float(np.median(e1)),
        "median_run2": float(np.median(e2)),
        "median_ratio": ratio,
        "wilcoxon_p": float(wil.pvalue),
    }

    H = h.rewards
    out["h_runs"] = {
        tag: {
            "summaries": len(H[tag]),
            "in_universe": len(set(H[tag]) & set(T)),
            "missing": sorted(set(T) - set(H[tag])),
            "null_reward": h.null_rewards[tag],
            "sum": sum(H[tag].values()),
            "rate_pct_scored": 100 * sum(H[tag].values()) / len(H[tag]),
            "rate_pct_nulls_as_fail": 100
            * sum(H[tag].values())
            / (len(H[tag]) + len(h.null_rewards[tag])),
            "err_files": len(h.err_files[tag]),
        }
        for tag in H_RUN_TAGS
    }
    pair_rates = []
    out["h_pairs"] = []
    for a_tag, b_tag in itertools.combinations(H_RUN_TAGS, 2):
        a, b = H[a_tag], H[b_tag]
        ts = [t for t in T if t in a and t in b]
        test = mcnemar(ts, a, b)
        low, high = clopper_pearson(test.discordant, len(ts))
        gap = 100 * (sum(a[t] for t in ts) - sum(b[t] for t in ts)) / len(ts)
        pair_rates.append((test.discordant / len(ts), high))
        out["h_pairs"].append(
            {"pair": [a_tag, b_tag], **test.as_dict(), "ci95": [low, high], "gap_pp": gap}
        )
    q_h = float(np.mean([rate for rate, _ in pair_rates]))
    bound = max(high for _, high in pair_rates)
    clean_test = mcnemar(clean, s1, s2)
    v_rate = clean_test.discordant / len(clean)
    sd_pp = 100 * math.sqrt(q_h * n_c) / n_c
    out["reference_noise"] = {
        "q_h": q_h,
        "discordance_bound": bound,
        "clean_discordance_rate": v_rate,
        "expected_gap_sd_pp": sd_pp,
        "gap_in_sd": gap_pp / sd_pp if sd_pp else None,
        "note": "restates the McNemar result; not independent evidence (review E11)",
    }
    out["v_vs_h"] = []
    for name, s in (("run1", s1), ("run2", s2)):
        for tag in H_RUN_TAGS:
            ts = [t for t in T if t in s and t in H[tag]]
            out["v_vs_h"].append({"pair": [name, tag], **mcnemar(ts, s, H[tag]).as_dict()})

    ts = [t for t in C if all(t in H[k] for k in H_RUN_TAGS)]
    succ = np.array([sum(H[k][t] >= 0.5 for k in H_RUN_TAGS) for t in ts])
    p_i = (succ + 0.5) / (3 + 1.0)
    sums_a = _bernoulli_row_sums(rng, p_i, model_draws)
    sums_b = _bernoulli_row_sums(rng, p_i, model_draws)
    g = 100 * (sums_a - sums_b) / len(ts)
    observed_bin = 100 * (sum(s1[t] >= 0.5 for t in ts) - sum(s2[t] >= 0.5 for t in ts)) / len(ts)
    out["h_only_model"] = {
        "n": len(ts),
        "sim_gap_sd_pp": float(g.std()),
        "observed_binary_gap_pp": observed_bin,
        "p_abs_gap_ge_observed": float((np.abs(g) >= abs(observed_bin) - 1e-9).mean()),
        "draws": model_draws,
        "note": "reporting-only; over-dispersed with three runs (v1 disclosure)",
    }
    if any(h.steps.values()):
        out["h_steps"] = {
            tag: {
                "n": len(h.steps[tag]),
                "median": float(np.median(list(h.steps[tag].values()))),
                "max": max(h.steps[tag].values()),
                "zero": sum(1 for v in h.steps[tag].values() if v == 0),
                "at_or_over_100": sum(1 for v in h.steps[tag].values() if v >= 100),
            }
            for tag in H_RUN_TAGS
            if h.steps.get(tag)
        }

    r1_fires = infra_share >= 0.5
    elapsed_shift = out["elapsed_clean"]["wilcoxon_p"] < 0.01 and abs(ratio - 1) >= 0.10
    any_domain = any(adj < 0.05 for adj in adjusted)
    r2_holds = (
        not r1_fires
        and clean_test.p >= 0.05
        and v_rate <= bound
        and not any_domain
        and not elapsed_shift
    )
    r3_fires = not r1_fires and (clean_test.p < 0.05 or v_rate > bound or elapsed_shift)
    out["decision"] = {
        "R1_infrastructure": r1_fires,
        "R2_rerun_noise": r2_holds,
        "R3_systematic": r3_fires,
        "verdict": "R1"
        if r1_fires
        else ("R2" if r2_holds else ("R3" if r3_fires else "inconclusive")),
        "reading": (
            "R3 means task-level non-exchangeable reruns (session shift present). It is not an "
            "operator contrast and does not fire the Q2 kill criterion (infrastructure or "
            "operator); see the v1 post-hoc record."
        ),
        "q2_kill_criterion_fires": r1_fires,
    }
    return out


def _bernoulli_row_sums(rng: np.random.Generator, p: np.ndarray, draws: int, chunk: int = 10_000):
    """Row sums of ``rng.random((draws, len(p))) < p`` drawn in row chunks."""
    sums = np.empty(draws, dtype=np.int64)
    done = 0
    while done < draws:
        rows = min(chunk, draws - done)
        sums[done : done + rows] = (rng.random((rows, p.size)) < p).sum(1)
        done += rows
    return sums


def v1_reproduction_checks(result: Mapping[str, Any]) -> dict[str, Any]:
    """Compare a seed-42 v1 analysis with the numbers v1 printed on the host."""
    rec = V1_RECORDED
    exact: list[tuple[str, Any, Any]] = []
    runs = result["runs"]
    for run in ("run1", "run2"):
        exact.append((f"{run}.scored", runs[run]["scored"], rec["scored"][run]))
        exact.append((f"{run}.sum", f"{runs[run]['sum']:.4f}", rec["sum"][run]))
        exact.append((f"{run}.passed_gt0", runs[run]["passed_gt0"], rec["passed_gt0"][run]))
    sets = result["sets"]
    exact += [
        ("common", sets["common"], rec["common"]),
        ("infra_flagged", sets["infra_flagged"], rec["infra_flagged"]),
        ("clean", sets["clean"], rec["clean"]),
        ("web_tasks", result["web_tasks"], rec["web_tasks"]),
    ]
    for mode, by_set in rec["mcnemar"].items():
        for name, (a_only, b_only, p) in by_set.items():
            got = result["mcnemar"][mode][name]
            exact.append((f"mcnemar.{mode}.{name}.a_only", got["a_only"], a_only))
            exact.append((f"mcnemar.{mode}.{name}.b_only", got["b_only"], b_only))
            exact.append((f"mcnemar.{mode}.{name}.p", f"{got['exact_p']:.4g}", p))
    dec = result["decomposition"]
    exact.append(("gap_pp", f"{dec['gap_pp']:.3f}", rec["gap_pp"]))
    exact.append(("inclusion_pp", f"{dec['inclusion_pp']:.3f}", rec["inclusion_pp"]))
    for key, value in rec["components_tasks"].items():
        exact.append((f"component.{key}.tasks", f"{dec['components_tasks'][key]:+.3f}", value))
        exact.append(
            (f"component.{key}.pp", f"{dec['components_pp'][key]:+.3f}", rec["components_pp"][key])
        )
    for label, (n, a_only, b_only, p) in rec["web_strata"].items():
        got = result["web_strata_clean"][label]
        exact.append(
            (
                f"web_strata.{label}",
                [got["n"], got["a_only"], got["b_only"], f"{got['exact_p']:.3g}"],
                [n, a_only, b_only, p],
            )
        )
    el = result["elapsed_clean"]
    exact += [
        ("elapsed.median_run1", f"{el['median_run1']:.1f}", rec["elapsed"]["median_run1"]),
        ("elapsed.median_run2", f"{el['median_run2']:.1f}", rec["elapsed"]["median_run2"]),
        ("elapsed.ratio", f"{el['median_ratio']:.3f}", rec["elapsed"]["ratio"]),
        ("elapsed.p", f"{el['wilcoxon_p']:.3g}", rec["elapsed"]["p"]),
    ]
    for tag, value in rec["h_sums"].items():
        exact.append((f"h_sum.{tag}", f"{result['h_runs'][tag]['sum']:.4f}", value))
    for got, (disc, rate, net) in zip(result["h_pairs"], rec["h_pairs"], strict=True):
        exact.append(
            (
                f"h_pair.{'-'.join(got['pair'])}",
                [
                    got["discordant"],
                    f"{got['discordance_rate']:.4f}",
                    got["a_only"] - got["b_only"],
                ],
                [disc, rate, net],
            )
        )
    ref = result["reference_noise"]
    exact += [
        ("q_h", f"{ref['q_h']:.4f}", rec["q_h"]),
        ("sd_pp", f"{ref['expected_gap_sd_pp']:.3f}", rec["sd_pp"]),
        ("gap_in_sd", f"{ref['gap_in_sd']:.2f}", rec["gap_in_sd"]),
    ]
    mismatches = [
        {"quantity": name, "got": got, "recorded": want} for name, got, want in exact if got != want
    ]
    monte_carlo = []
    for name, want in rec["sign_flip_p"].items():
        got = result["sign_flip"][name]["p"]
        monte_carlo.append(
            _mc_check(f"sign_flip.{name}", got, want, result["sign_flip"][name]["draws"])
        )
    got = result["h_only_model"]["p_abs_gap_ge_observed"]
    monte_carlo.append(
        _mc_check("h_only_model.p", got, rec["h_model_p"], result["h_only_model"]["draws"])
    )
    mc_fail = [c for c in monte_carlo if not c["within_4_se"]]
    return {
        "status": "PASS" if not mismatches and not mc_fail else "FAIL",
        "exact_quantities_checked": len(exact),
        "exact_mismatches": mismatches,
        "monte_carlo": monte_carlo,
        "source": "host analysis/run_output.txt sha256 a24e1590... (scout run, 2026-10-07)",
    }


def _mc_check(name: str, got: float, recorded: str, draws: int) -> dict[str, Any]:
    want = float(recorded)
    se = math.sqrt(max(want * (1 - want), 1e-12) / draws)
    return {
        "quantity": name,
        "got": got,
        "recorded": recorded,
        "identical_as_printed": f"{got:.4g}" == recorded,
        "within_4_se": abs(got - want) <= 4 * se + 1e-12,
    }


def holo3_domain_control(m: V1Matrix) -> dict[str, Any]:
    """Positive control: all 20 leaderboard domain cells and both totals."""
    problems: list[str] = []
    for run, scores in (("run1", m.s1), ("run2", m.s2)):
        scored = {t: v for t, v in scores.items() if v is not None}
        expected = HOLO3_LEADERBOARD[run]
        got_total = cell(sum(scored.values()), len(scored))
        if got_total != expected["total"]:
            problems.append(f"{run} total {got_total} != {expected['total']}")
        got_cells = domain_cells(scored, m.domain_of)
        for domain in DOMAINS:
            if got_cells.get(domain) != expected["cells"][domain]:
                problems.append(
                    f"{run} {domain} {got_cells.get(domain)} != {expected['cells'][domain]}"
                )
    return {"status": "PASS" if not problems else "FAIL", "cells_checked": 22, "problems": problems}


def summary_control(pkg: VerifiedPackage, m: V1Matrix) -> dict[str, Any]:
    """The run summaries shipped in the package agree with the per-task files."""
    problems: list[str] = []
    for key, scores in (("run1_merged_with_repair", m.s1), ("run2_final", m.s2)):
        summary = pkg.summaries[key]
        scored = [v for v in scores.values() if v is not None]
        want = {
            "total_tasks": len(m.tasks),
            "scored": len(scored),
            "passed": sum(1 for v in scored if v > 0),
            "errors": sum(1 for v in scores.values() if v is None),
        }
        for field_name, value in want.items():
            if summary.get(field_name) != value:
                problems.append(f"{key}.{field_name} {summary.get(field_name)} != {value}")
        if (
            summary.get("score") is None
            or abs(summary["score"] - sum(scored) / len(scored)) > 1e-12
        ):
            problems.append(f"{key}.score disagrees with per-task mean")
    mismatched = 0
    for key in RUN_DIRS:
        for task, record in pkg.status[key].items():
            text = pkg.result_txt[key].get(task)
            if record.get("status") == "completed" and (
                text is None or float(text) != float(record["score"])
            ):
                mismatched += 1
    if mismatched:
        problems.append(f"{mismatched} result.txt values disagree with status.json")
    return {"status": "PASS" if not problems else "FAIL", "problems": problems}


# --------------------------------------------------------------------------- #
# Reviewed-plan corrections (E3, E5) and power (E12)
# --------------------------------------------------------------------------- #


def five_run_comparison(m: V1Matrix, h: HRuns) -> dict[str, Any]:
    """Rates, pairwise z and idiosyncratic outcomes on tasks all five runs scored."""
    runs: dict[str, dict[str, float]] = {
        "run1": {t: v for t, v in m.s1.items() if v is not None},
        "run2": {t: v for t, v in m.s2.items() if v is not None},
        **{f"H{tag}": h.rewards[tag] for tag in H_RUN_TAGS},
    }
    common = [t for t in m.tasks if all(t in s for s in runs.values())]
    rates = {name: 100 * sum(s[t] for t in common) / len(common) for name, s in runs.items()}
    binary = {
        name: 100 * sum(1 for t in common if s[t] >= 0.5) / len(common) for name, s in runs.items()
    }
    pairs = []
    for a, b in itertools.combinations(runs, 2):
        pairs.append({"pair": [a, b], **mcnemar(common, runs[a], runs[b]).as_dict()})
    idiosyncratic: dict[str, dict[str, int]] = {}
    for name, scores in runs.items():
        others = [o for o in runs if o != name]
        consensus_pass = [t for t in common if all(runs[o][t] >= 0.5 for o in others)]
        consensus_fail = [t for t in common if all(runs[o][t] < 0.5 for o in others)]
        idiosyncratic[name] = {
            "fails_consensus_pass": sum(1 for t in consensus_pass if scores[t] < 0.5),
            "consensus_pass_tasks": len(consensus_pass),
            "passes_consensus_fail": sum(1 for t in consensus_fail if scores[t] >= 0.5),
            "consensus_fail_tasks": len(consensus_fail),
        }
    return {
        "n_common": len(common),
        "rates_pct": rates,
        "pass_rates_pct_binary": binary,
        "pairs": pairs,
        "idiosyncratic": idiosyncratic,
        "reading": "run1 is high relative to the H runs; run2 has more unique failures; "
        "which run is the outlier is indeterminate with five runs on two harnesses",
    }


def opencua_reference(
    sets: Sequence[OpenCUASet],
    holo3_z: float,
    h_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """EXPLORATORY: exchangeability of maintainer reruns (OpenCUA, H-H)."""
    per_set: dict[str, Any] = {}
    parts = []
    reference_z: list[float] = []
    for s in sets:
        turns = s.turns
        totals = {
            name: {"sum": sum(v.values()), "n": len(v), "cell": cell(sum(v.values()), len(v))}
            for name, v in turns.items()
        }
        pairs = []
        for a, b in itertools.combinations(sorted(turns), 2):
            common = sorted(set(turns[a]) & set(turns[b]))
            test = mcnemar(common, turns[a], turns[b])
            gap = (
                100
                * (sum(turns[a][t] for t in common) - sum(turns[b][t] for t in common))
                / len(common)
            )
            pairs.append({"pair": [a, b], **test.as_dict(), "gap_pp": gap})
            reference_z.append(abs(test.z))
        common_all = sorted(set.intersection(*(set(v) for v in turns.values())))
        matrix = np.array([[turns[k][t] >= 0.5 for k in sorted(turns)] for t in common_all], float)
        part = two_way_variance_ratio(matrix)
        parts.append(part)
        per_set[s.key] = {
            "turn_totals": totals,
            "pairs": pairs,
            "variance": part,
            "max_abs_z": max(abs(p["z"]) for p in pairs),
            "member_manifest_sha256": s.member_manifest_sha256,
            "result_txt_members": s.members_read,
        }
    for pair in h_pairs:
        reference_z.append(abs(pair["z"]))
    pooled = pooled_variance_ratio(parts)
    max_ref = max(reference_z) if reference_z else float("nan")
    rank = 1 + sum(1 for z in reference_z if z > abs(holo3_z))
    return {
        "label": "EXPLORATORY (inspected during review before any registration)",
        "sets": per_set,
        "pooled_variance_ratio": pooled,
        "reference_pairs": len(reference_z),
        "max_abs_z_reference": max_ref,
        "holo3_abs_z": abs(holo3_z),
        "holo3_rank_among_all": rank,
        "pair_specific_session_shift": bool(abs(holo3_z) > max_ref and pooled["ratio"] <= 1.5),
    }


def opencua_leaderboard_control(sets: Sequence[OpenCUASet]) -> dict[str, Any]:
    """Each archive's three turn totals equal its three leaderboard rows (bijection)."""
    problems: list[str] = []
    matched: dict[str, dict[str, int]] = {}
    for s in sets:
        expected = dict(OPENCUA_LEADERBOARD[s.key])
        matched[s.key] = {}
        for turn in sorted(s.turns):
            got_sum = sum(s.turns[turn].values())
            got_n = len(s.turns[turn])
            hit = next(
                (
                    row
                    for row, text in expected.items()
                    if _cell_value(text)[1] == got_n
                    and abs(_cell_value(text)[0] - got_sum) < 0.005 + 1e-9
                ),
                None,
            )
            if hit is None:
                problems.append(
                    f"{s.key} {turn}: {cell(got_sum, got_n)} matches no leaderboard row"
                )
            else:
                matched[s.key][turn] = hit
                expected.pop(hit)
        if len(s.turns) != 3:
            problems.append(f"{s.key}: {len(s.turns)} turns, expected 3")
    return {
        "status": "PASS" if not problems else "FAIL",
        "turns_checked": sum(len(s.turns) for s in sets),
        "turn_to_row": matched,
        "problems": problems,
    }


def power_summary(q_h: float) -> dict[str, Any]:
    return {
        "q_reference": q_h,
        "mde_pp_single_two_run_contrast": {
            "n359": 100 * mde_two_run_contrast(q_h, 359),
            "n120": 100 * mde_two_run_contrast(q_h, 120),
        },
        "note": "a single two-run contrast; not comparable with the dossier's interaction MDE, and "
        "a session variance component adds a floor that more tasks do not remove (review E12)",
    }
