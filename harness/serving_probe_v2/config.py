"""Load and validate the serving-throughput-probe-v2 contract.

The v2 contract keeps v1's schema for models, engines, points and jobs (the v1
validators in ``harness.serving_probe.config`` check them) and adds:

* ``required`` on every point: required points own reserved time in the launch
  window; optional points and every rerun run only from slack;
* the second point of every phase is its warm-up, a replay of the largest
  registered prompt shape after which the engine's reservation is measured; the
  loader refuses a warm-up that any later point of the phase exceeds in prompt
  tokens per request, images per request or tokens in flight;
* ``start_minutes`` per phase (G0.8 and the engine start) and ``preamble_minutes``
  (gates G0.0 to G0.4): the preamble plus every phase's start allowance and the
  caps of its required points must fit before the soft stop;
* every replay uses prebuilt (fixed) history, so a step's prompt never depends
  on what an engine generated;
* only server points: v2 has no offline job and no A/A point.

Validation fails closed, as in v1.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from harness.serving_probe.config import (
    DIGEST_REF_RE,
    GIT_RE,
    IMAGE_ID_RE,
    EngineSpec,
    JobSpec,
    PhaseSpec,
    PointSpec,
    ProbeConfig,
    ProbeConfigError,
    _positive_int,
    _positive_number,
    _validate_flags,
    _validate_job,
    _validate_models,
    _validate_point,
)
from harness.serving_probe.prompts import (
    IMAGE_WRAPPER_TOKENS,
    HarnessShape,
    modeled_prompt_tokens,
    visible_images,
)

EXPERIMENT_ID = "serving-throughput-probe-v2"
#: v2 measures server points only (no offline Q1 job, no A/A point).
ALLOWED_KINDS = {"smoke-server", "open-loop", "replay"}
REQUIRED_SECTIONS = (
    "gates",
    "validity",
    "dummy_admissibility",
    "stop",
    "sampling",
    "server",
    "budget",
)
VALIDITY_KEYS = (
    "contamination_margin_mib",
    "own_footprint_margin_mib",
    "unattributed_margin_mib",
    "frontend_cpu_flag_pct",
    "unstable_relative_range",
    "reruns_per_invalid_point",
    "reservation_window_s",
    "min_gpu_sample_fraction",
    "min_apps_snapshot_fraction",
)
X1_KEYS = (
    "max_open_loop_delta",
    "max_replay_latency_delta",
    "max_replay_delta_se",
    "max_a1_seed_range",
)
STOP_KEYS = ("soft_fraction", "hard_margin_minutes", "in_flight_grace_s", "preamble_minutes")


@dataclass(frozen=True)
class PointShape:
    """The size of one point's largest request, used for the warm-up dominance check."""

    max_prompt_tokens: int
    max_images: int
    in_flight_tokens: int


def is_required(point: PointSpec) -> bool:
    return point.get("required") is True


def point_shape(point: PointSpec, image_tokens: int) -> PointShape:
    """Largest modelled prompt, images per request and tokens in flight of a point."""
    output = int(point["output_tokens"])
    if point.kind == "replay":
        shape = HarnessShape(
            harness=str(point["harness"]),
            system_tokens=int(point["system_tokens"]),
            task_tokens=int(point["task_tokens"]),
            action_tokens=int(point["action_tokens"]),
            response_tokens=int(point["prebuilt_response_tokens"]),
            a11y_tokens=int(point["a11y_tokens"]),
            image_tokens=image_tokens,
            history_n=int(point["history_n"]),
            image_max=int(point.get("image_max", 20)),
            fold_size=int(point.get("fold_size", 10)),
        )
        first = int(point["start_depth"]) + 1
        steps = range(first, first + int(point["steps"]))
        prompt = max(modeled_prompt_tokens(shape, step) for step in steps)
        images = max(visible_images(shape, step) for step in steps)
        concurrency = int(point["episodes"])
    else:
        images = int(point["images"])
        prompt = (
            int(point["prefix_tokens"])
            + int(point["body_tokens"])
            + images * (image_tokens + IMAGE_WRAPPER_TOKENS)
        )
        concurrency = int(point["concurrency"])
    return PointShape(prompt, images, concurrency * (prompt + output))


def check_warmup_dominates(phase: PhaseSpec, image_tokens: int) -> dict[str, Any]:
    """The phase's warm-up is at least as large as every later point (fails closed)."""
    warmup = phase.points[1]
    if warmup.get("role") != "warm-up" or warmup.kind != "replay":
        raise ProbeConfigError(
            f"phase {phase.phase_id}: the second point must be its replay warm-up"
        )
    reference = point_shape(warmup, image_tokens)
    for point in phase.points[2:]:
        shape = point_shape(point, image_tokens)
        for field in ("max_prompt_tokens", "max_images", "in_flight_tokens"):
            if getattr(shape, field) > getattr(reference, field):
                raise ProbeConfigError(
                    f"phase {phase.phase_id}: point {point.point_id} exceeds the warm-up in "
                    f"{field} ({getattr(shape, field)} > {getattr(reference, field)})"
                )
    return {
        "warmup": warmup.point_id,
        "max_prompt_tokens": reference.max_prompt_tokens,
        "max_images": reference.max_images,
        "in_flight_tokens": reference.in_flight_tokens,
    }


def phase_start_minutes(raw_job: Mapping[str, Any], phase_id: str) -> float:
    for phase in raw_job["phases"]:
        if phase["id"] == phase_id:
            return _positive_number(phase.get("start_minutes"), f"{phase_id}.start_minutes")
    raise ProbeConfigError(f"unknown phase {phase_id}")


def required_minutes(phase: PhaseSpec, start_minutes: float) -> float:
    """Reserved time of a phase: its start allowance plus the caps of its required points."""
    return start_minutes + sum(p.max_minutes for p in phase.points if is_required(p))


def launch_window_check(config: ProbeConfig, job_id: str) -> dict[str, Any]:
    """Static ledger check: the preamble and every phase's reserved time fit the soft stop."""
    job = config.job(job_id)
    raw_job = config.raw["jobs"][job_id]
    stop = config.section("stop")
    soft_minutes = float(stop["soft_fraction"]) * job.allocation_minutes
    preamble = float(stop["preamble_minutes"])
    phases = [
        {
            "phase": phase.phase_id,
            "start_minutes": phase_start_minutes(raw_job, phase.phase_id),
            "required_point_minutes": sum(p.max_minutes for p in phase.points if is_required(p)),
        }
        for phase in job.phases
    ]
    reserved = preamble + sum(p["start_minutes"] + p["required_point_minutes"] for p in phases)
    if reserved > soft_minutes + 1e-9:
        raise ProbeConfigError(
            f"job {job_id}: reserved time {reserved:.2f} min (preamble, phase starts and "
            f"required caps) exceeds the soft stop at {soft_minutes:.2f} min"
        )
    return {
        "soft_minutes": soft_minutes,
        "preamble_minutes": preamble,
        "phases": phases,
        "reserved_minutes": reserved,
        "worst_case_slack_minutes": soft_minutes - reserved,
    }


def _check_v2_points(points: Mapping[str, PointSpec]) -> None:
    for point in points.values():
        if point.kind not in ALLOWED_KINDS:
            raise ProbeConfigError(f"point {point.point_id}: kind {point.kind} is not used in v2")
        if not isinstance(point.get("required"), bool):
            raise ProbeConfigError(f"point {point.point_id}: required must be true or false")
        if point.kind == "replay" and point.get("history") != "prebuilt":
            raise ProbeConfigError(
                f"point {point.point_id}: v2 replays use prebuilt history (identical prompts)"
            )
        if point.get("role") not in (None, "warm-up"):
            raise ProbeConfigError(f"point {point.point_id}: unknown role {point.get('role')!r}")


def _check_v2_job(job: JobSpec, raw_job: Mapping[str, Any], image_tokens: int) -> None:
    for phase, raw_phase in zip(job.phases, raw_job["phases"], strict=True):
        if "reserve_minutes" in raw_phase:
            raise ProbeConfigError(
                f"phase {phase.phase_id}: v2 reserves time with start_minutes and required caps"
            )
        if len(phase.points) < 3:
            raise ProbeConfigError(f"phase {phase.phase_id}: needs a smoke, a warm-up and points")
        smoke, warmup = phase.points[0], phase.points[1]
        if not (is_required(smoke) and is_required(warmup)):
            raise ProbeConfigError(f"phase {phase.phase_id}: smoke and warm-up are required")
        for point in phase.points[2:]:
            if point.get("role") == "warm-up":
                raise ProbeConfigError(f"phase {phase.phase_id}: one warm-up per phase")
        seen_optional = False
        for point in phase.points[2:]:
            if not is_required(point):
                seen_optional = True
            elif seen_optional:
                raise ProbeConfigError(
                    f"phase {phase.phase_id}: required point {point.point_id} is listed after "
                    "an optional one (required points come first)"
                )
        check_warmup_dominates(phase, image_tokens)


def validate_config(raw: Any, *, path: Path, sha256: str) -> ProbeConfig:
    """Validate a parsed v2 contract and return v1's typed view of it."""
    if not isinstance(raw, Mapping) or raw.get("schema_version") != 1:
        raise ProbeConfigError("config must be a schema_version: 1 mapping")
    if raw.get("experiment_id") != EXPERIMENT_ID:
        raise ProbeConfigError(f"config experiment_id must be {EXPERIMENT_ID}")
    prereg = raw.get("preregistration")
    if prereg != f"program/preregistrations/{EXPERIMENT_ID}.md":
        raise ProbeConfigError("preregistration must name the v2 registration file")
    vllm = raw.get("vllm")
    if not isinstance(vllm, Mapping) or not GIT_RE.fullmatch(str(vllm.get("commit", ""))):
        raise ProbeConfigError("vllm.commit must be a 40-hex commit")
    variants = vllm.get("image_variants")
    if not isinstance(variants, Mapping) or set(variants) != {"cu129"}:
        raise ProbeConfigError("v2 runs on the cu129 image only (no pre-approved cu130 retry)")
    variant = variants["cu129"]
    if not isinstance(variant, Mapping):
        raise ProbeConfigError("image variant cu129 must be a mapping")
    if not DIGEST_REF_RE.fullmatch(str(variant.get("base_image", ""))):
        raise ProbeConfigError("image variant cu129: base_image must be pinned by digest")
    if not IMAGE_ID_RE.fullmatch(str(variant.get("base_image_id", ""))):
        raise ProbeConfigError("image variant cu129: base_image_id must be sha256:<64 hex>")
    env = variant.get("env", {})
    if not isinstance(env, Mapping) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in env.items()
    ):
        raise ProbeConfigError("image variant cu129: env must map strings to strings")

    seeds = raw.get("primary_seeds")
    if (
        not isinstance(seeds, list)
        or len(seeds) < 3
        or len(set(seeds)) != len(seeds)
        or not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
    ):
        raise ProbeConfigError("primary_seeds must list at least three distinct integers")
    for section in REQUIRED_SECTIONS:
        if not isinstance(raw.get(section), Mapping):
            raise ProbeConfigError(f"config section {section!r} is missing")
    for section, keys in (
        ("validity", VALIDITY_KEYS),
        ("dummy_admissibility", X1_KEYS),
        ("stop", STOP_KEYS),
    ):
        for key in keys:
            _positive_number(raw[section].get(key), f"{section}.{key}", allow_zero=False)
    if int(raw["validity"]["reruns_per_invalid_point"]) != 1:
        raise ProbeConfigError("validity.reruns_per_invalid_point is 1 (one rerun per point)")
    _positive_number(raw["sampling"].get("apps_interval_s"), "sampling.apps_interval_s")
    screenshot = raw.get("screenshot")
    if not isinstance(screenshot, Mapping):
        raise ProbeConfigError("screenshot size is missing")
    _positive_int(screenshot.get("width"), "screenshot.width")
    _positive_int(screenshot.get("height"), "screenshot.height")

    models = _validate_models(raw.get("models"))
    raw_engines = raw.get("engines")
    if not isinstance(raw_engines, Mapping) or not raw_engines:
        raise ProbeConfigError("engines must be a non-empty mapping")
    engines: dict[str, EngineSpec] = {}
    for engine_id, entry in raw_engines.items():
        if not isinstance(entry, Mapping) or entry.get("mode") != "server":
            raise ProbeConfigError(f"engine {engine_id}: v2 engines are vllm serve engines")
        model = entry.get("model")
        if model not in models:
            raise ProbeConfigError(f"engine {engine_id}: unknown model {model!r}")
        load_format = entry.get("load_format")
        if load_format not in {"auto", "dummy"}:
            raise ProbeConfigError(f"engine {engine_id}: load_format must be auto or dummy")
        if models[model]["weights"] != "real":
            raise ProbeConfigError(f"engine {engine_id}: v2 serves the receipted real-weight model")
        flags = _validate_flags(str(engine_id), entry.get("flags"))
        engines[str(engine_id)] = EngineSpec(str(engine_id), "server", model, load_format, flags)

    raw_points = raw.get("points")
    if not isinstance(raw_points, Mapping) or not raw_points:
        raise ProbeConfigError("points must be a non-empty mapping")
    points = {
        str(point_id): _validate_point(str(point_id), entry)
        for point_id, entry in raw_points.items()
    }
    _check_v2_points(points)
    for point in points.values():
        control = point.get("control_of")
        if control is not None and control not in points:
            raise ProbeConfigError(f"point {point.point_id}: control_of names unknown {control!r}")

    raw_jobs = raw.get("jobs")
    if not isinstance(raw_jobs, Mapping) or set(raw_jobs) != {"a"}:
        raise ProbeConfigError("v2 has exactly one job, a")
    image_tokens = int(raw["budget"]["q2"]["image_tokens"])
    jobs: dict[str, JobSpec] = {}
    for job_id, entry in raw_jobs.items():
        job = _validate_job(str(job_id), entry, models, engines, points)
        _check_v2_job(job, entry, image_tokens)
        jobs[str(job_id)] = job
    config = ProbeConfig(
        path=path,
        sha256=sha256,
        raw=raw,
        primary_seeds=tuple(seeds),
        models=models,
        engines=engines,
        points=points,
        jobs=jobs,
    )
    for job_id in jobs:
        launch_window_check(config, job_id)
    return config


def load_config(path: Path) -> ProbeConfig:
    """Read, hash and validate the v2 contract."""
    data = path.read_bytes()
    try:
        raw = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise ProbeConfigError(f"config is not valid YAML: {exc}") from exc
    return validate_config(raw, path=path, sha256=hashlib.sha256(data).hexdigest())


def phase_points(phase: PhaseSpec) -> dict[str, Sequence[PointSpec]]:
    """The phase's points by role: smoke, warm-up, required and optional measured points."""
    measured = phase.points[2:]
    return {
        "smoke": phase.points[:1],
        "warmup": phase.points[1:2],
        "required": tuple(p for p in measured if is_required(p)),
        "optional": tuple(p for p in measured if not is_required(p)),
    }
