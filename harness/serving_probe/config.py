"""Load and validate the serving-throughput probe contract.

The YAML contract under ``experiments/serving/`` is the only source of engine
flags, points, seeds and thresholds. Validation fails closed: an unknown engine
flag, a speculative-decoding key, a point used twice in one job or a seed list
that differs from the declared primary seeds is a contract error, never a
default.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
DIGEST_REF_RE = re.compile(r"^[a-z0-9./-]+@sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,63}$")
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,79}$")

#: Engine flags admitted in the contract, in the order they are rendered.
ENGINE_FLAG_ORDER: tuple[str, ...] = (
    "tensor_parallel_size",
    "dtype",
    "seed",
    "max_model_len",
    "gpu_memory_utilization",
    "max_num_seqs",
    "max_num_batched_tokens",
    "enable_prefix_caching",
    "generation_config",
    "limit_mm_per_prompt",
)
#: Keys that would enable MTP or speculative decoding (vLLM #53912 is open).
FORBIDDEN_FLAG_FRAGMENTS: tuple[str, ...] = ("speculative", "mtp", "num_speculative", "draft")

POINT_KINDS = {"smoke-server", "open-loop", "replay", "aa", "smoke-offline", "offline"}
SERVER_KINDS = {"smoke-server", "open-loop", "replay", "aa"}
OFFLINE_KINDS = {"smoke-offline", "offline"}
IMAGE_KINDS = {"jpeg-random", "png-rendered"}
WEIGHT_KINDS = {"real", "admission-token", "dummy"}

_REQUIRED_POINT_KEYS: dict[str, tuple[str, ...]] = {
    "smoke-server": (
        "prefix_tokens",
        "body_tokens",
        "images",
        "image_kind",
        "output_tokens",
        "thinking",
        "concurrency",
        "requests",
    ),
    "open-loop": (
        "prefix_tokens",
        "body_tokens",
        "images",
        "image_kind",
        "output_tokens",
        "thinking",
        "concurrency",
        "requests",
    ),
    "aa": (
        "prefix_tokens",
        "body_tokens",
        "images",
        "image_kind",
        "output_tokens",
        "thinking",
        "requests",
        "arms",
    ),
    "replay": (
        "harness",
        "episodes",
        "start_depth",
        "steps",
        "output_tokens",
        "thinking",
        "a11y_tokens",
        "system_tokens",
        "task_tokens",
        "action_tokens",
        "prebuilt_response_tokens",
        "t_env_s",
        "stagger_s",
        "history_n",
    ),
    "smoke-offline": ("input_tokens", "output_tokens", "prompts", "n", "temperature"),
    "offline": ("input_tokens", "output_tokens", "prompts", "n", "temperature"),
}


class ProbeConfigError(ValueError):
    """Raised when the probe contract is malformed or internally inconsistent."""


@dataclass(frozen=True)
class EngineSpec:
    engine_id: str
    mode: str
    model: str
    load_format: str
    flags: Mapping[str, Any]

    def server_argv(self, model_dir: str, *, host: str, port: int, served_name: str) -> list[str]:
        """Return the exact ``vllm serve`` argv for this engine (no shell)."""
        if self.mode != "server":
            raise ProbeConfigError(f"{self.engine_id} is not a server engine")
        argv = [
            "vllm",
            "serve",
            model_dir,
            "--served-model-name",
            served_name,
            "--host",
            host,
            "--port",
            str(port),
            "--load-format",
            self.load_format,
            "--disable-uvicorn-access-log",
        ]
        argv.extend(render_engine_flags(self.flags))
        return argv

    def offline_kwargs(self) -> dict[str, Any]:
        """Return keyword arguments for ``vllm.LLM`` (text-only offline engine)."""
        if self.mode != "offline":
            raise ProbeConfigError(f"{self.engine_id} is not an offline engine")
        kwargs = {key: self.flags[key] for key in ENGINE_FLAG_ORDER if key in self.flags}
        kwargs["load_format"] = self.load_format
        kwargs["disable_log_stats"] = False
        return kwargs


@dataclass(frozen=True)
class PointSpec:
    point_id: str
    kind: str
    seed: int
    max_minutes: float
    params: Mapping[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.params[key]


@dataclass(frozen=True)
class PhaseSpec:
    phase_id: str
    engine: EngineSpec
    role: str
    reserve_minutes: float
    points: tuple[PointSpec, ...]


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    title: str
    allocation_minutes: int
    lane_model: str
    phases: tuple[PhaseSpec, ...]

    @property
    def mode(self) -> str:
        modes = {phase.engine.mode for phase in self.phases}
        if len(modes) != 1:
            raise ProbeConfigError(f"job {self.job_id} mixes engine modes {sorted(modes)}")
        return modes.pop()

    def pinned_models(self) -> list[str]:
        """Models whose metadata receipt must be pinned on the command line."""
        pinned = []
        for phase in self.phases:
            if phase.engine.model != self.lane_model and phase.engine.model not in pinned:
                pinned.append(phase.engine.model)
        return pinned


@dataclass(frozen=True)
class ProbeConfig:
    path: Path
    sha256: str
    raw: Mapping[str, Any]
    primary_seeds: tuple[int, ...]
    models: Mapping[str, Mapping[str, Any]]
    engines: Mapping[str, EngineSpec]
    points: Mapping[str, PointSpec]
    jobs: Mapping[str, JobSpec]

    @property
    def experiment_id(self) -> str:
        return str(self.raw["experiment_id"])

    @property
    def preregistration(self) -> str:
        return str(self.raw["preregistration"])

    def section(self, name: str) -> Mapping[str, Any]:
        value = self.raw.get(name)
        if not isinstance(value, Mapping):
            raise ProbeConfigError(f"config section {name!r} is missing")
        return value

    def job(self, job_id: str) -> JobSpec:
        if job_id not in self.jobs:
            raise ProbeConfigError(f"unknown job {job_id!r}; expected one of {sorted(self.jobs)}")
        return self.jobs[job_id]


def render_engine_flags(flags: Mapping[str, Any]) -> list[str]:
    """Render admitted engine flags as ``vllm serve`` CLI arguments."""
    argv: list[str] = []
    for key in ENGINE_FLAG_ORDER:
        if key not in flags:
            continue
        value = flags[key]
        option = "--" + key.replace("_", "-")
        if isinstance(value, bool):
            argv.append(option if value else "--no-" + key.replace("_", "-"))
        elif isinstance(value, Mapping):
            argv.extend([option, json.dumps(value, sort_keys=True, separators=(",", ":"))])
        else:
            argv.extend([option, str(value)])
    return argv


def _require(mapping: Mapping[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise ProbeConfigError(f"{context}: missing {key!r}")
    return mapping[key]


def _positive_int(value: Any, context: str, *, minimum: int = 1) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ProbeConfigError(f"{context} must be an integer >= {minimum}")
    return value


def _positive_number(value: Any, context: str, *, allow_zero: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProbeConfigError(f"{context} must be a number")
    if value < 0 or (value == 0 and not allow_zero):
        raise ProbeConfigError(f"{context} must be positive")
    return float(value)


def _validate_flags(engine_id: str, flags: Any) -> dict[str, Any]:
    if not isinstance(flags, Mapping):
        raise ProbeConfigError(f"engine {engine_id}: flags must be a mapping")
    for key in flags:
        lowered = str(key).lower()
        if any(fragment in lowered for fragment in FORBIDDEN_FLAG_FRAGMENTS):
            raise ProbeConfigError(f"engine {engine_id}: speculative/MTP flag {key!r} is banned")
        if key not in ENGINE_FLAG_ORDER:
            raise ProbeConfigError(f"engine {engine_id}: flag {key!r} is not admitted")
    for key in ("tensor_parallel_size", "max_model_len", "max_num_seqs", "max_num_batched_tokens"):
        _positive_int(_require(flags, key, f"engine {engine_id}"), f"{engine_id}.{key}")
    utilization = _require(flags, "gpu_memory_utilization", f"engine {engine_id}")
    if not isinstance(utilization, float) or not 0.1 <= utilization <= 0.95:
        raise ProbeConfigError(f"engine {engine_id}: gpu_memory_utilization must be in [0.1, 0.95]")
    if flags.get("enable_prefix_caching") is not True:
        raise ProbeConfigError(f"engine {engine_id}: the probe measures prefix caching on")
    return dict(flags)


def _validate_point(point_id: str, raw: Any) -> PointSpec:
    if not ID_RE.fullmatch(point_id):
        raise ProbeConfigError(f"point id {point_id!r} is not a safe slug")
    if not isinstance(raw, Mapping):
        raise ProbeConfigError(f"point {point_id}: must be a mapping")
    kind = raw.get("kind")
    if kind not in POINT_KINDS:
        raise ProbeConfigError(f"point {point_id}: unknown kind {kind!r}")
    for key in _REQUIRED_POINT_KEYS[kind]:
        _require(raw, key, f"point {point_id}")
    seed = raw.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ProbeConfigError(f"point {point_id}: seed must be a non-negative integer")
    max_minutes = _positive_number(raw.get("max_minutes"), f"point {point_id}.max_minutes")
    params = {
        key: value for key, value in raw.items() if key not in {"kind", "seed", "max_minutes"}
    }
    if kind in SERVER_KINDS and kind != "replay":
        if params["image_kind"] not in IMAGE_KINDS:
            raise ProbeConfigError(f"point {point_id}: image_kind must be one of {IMAGE_KINDS}")
        _positive_int(params["images"], f"{point_id}.images", minimum=0)
        _positive_int(params["output_tokens"], f"{point_id}.output_tokens")
        _positive_int(params["requests"], f"{point_id}.requests")
    if kind in {"smoke-server", "open-loop"}:
        _positive_int(params["concurrency"], f"{point_id}.concurrency")
    if kind == "smoke-server" and params["images"] < 1:
        raise ProbeConfigError(f"point {point_id}: the smoke needs an image for the G0.6 check")
    if kind == "aa":
        arms = params["arms"]
        if (
            not isinstance(arms, list)
            or len(arms) != 2
            or not all(isinstance(arm, int) and arm >= 1 for arm in arms)
        ):
            raise ProbeConfigError(f"point {point_id}: arms must be two concurrency levels")
    if kind == "replay":
        if params["harness"] not in {"h1", "h2"}:
            raise ProbeConfigError(f"point {point_id}: harness must be h1 or h2")
        _positive_int(params["episodes"], f"{point_id}.episodes")
        _positive_int(params["steps"], f"{point_id}.steps")
        _positive_int(params["start_depth"], f"{point_id}.start_depth", minimum=0)
        _positive_int(params["history_n"], f"{point_id}.history_n")
        _positive_number(params["t_env_s"], f"{point_id}.t_env_s", allow_zero=True)
        _positive_number(params["stagger_s"], f"{point_id}.stagger_s", allow_zero=True)
        if params["harness"] == "h2":
            for key in ("image_max", "fold_size"):
                _positive_int(_require(params, key, f"point {point_id}"), f"{point_id}.{key}")
    if kind in OFFLINE_KINDS:
        for key in ("input_tokens", "output_tokens", "prompts", "n"):
            _positive_int(params[key], f"{point_id}.{key}")
    control = params.get("control_of")
    if control is not None and not isinstance(control, str):
        raise ProbeConfigError(f"point {point_id}: control_of must name a point")
    return PointSpec(point_id, kind, seed, max_minutes, params)


def _validate_models(raw: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(raw, Mapping) or not raw:
        raise ProbeConfigError("models must be a non-empty mapping")
    models: dict[str, Mapping[str, Any]] = {}
    for model_id, entry in raw.items():
        if not MODEL_ID_RE.fullmatch(str(model_id)) or not isinstance(entry, Mapping):
            raise ProbeConfigError(f"model {model_id!r} is malformed")
        if not GIT_RE.fullmatch(str(entry.get("revision", ""))):
            raise ProbeConfigError(f"model {model_id}: revision must be a 40-hex commit")
        if "/" not in str(entry.get("repo_id", "")):
            raise ProbeConfigError(f"model {model_id}: repo_id is malformed")
        weights = entry.get("weights")
        if weights not in WEIGHT_KINDS:
            raise ProbeConfigError(f"model {model_id}: weights must be one of {WEIGHT_KINDS}")
        if weights in {"real", "admission-token"}:
            for key in ("receipt_sha256", "artifact_root_sha256"):
                if not SHA_RE.fullmatch(str(entry.get(key, ""))):
                    raise ProbeConfigError(f"model {model_id}: {key} must be a 64-hex digest")
        models[str(model_id)] = entry
    return models


def validate_config(raw: Any, *, path: Path, sha256: str) -> ProbeConfig:
    """Validate a parsed contract and return its typed view."""
    if not isinstance(raw, Mapping) or raw.get("schema_version") != 1:
        raise ProbeConfigError("config must be a schema_version: 1 mapping")
    if raw.get("experiment_id") != "serving-throughput-probe-v1":
        raise ProbeConfigError("config experiment_id must be serving-throughput-probe-v1")
    prereg = raw.get("preregistration")
    if not isinstance(prereg, str) or not prereg.startswith("program/preregistrations/"):
        raise ProbeConfigError("preregistration must name a file under program/preregistrations/")
    vllm = raw.get("vllm")
    if not isinstance(vllm, Mapping) or not GIT_RE.fullmatch(str(vllm.get("commit", ""))):
        raise ProbeConfigError("vllm.commit must be a 40-hex commit")
    variants = vllm.get("image_variants")
    if not isinstance(variants, Mapping) or "cu129" not in variants:
        raise ProbeConfigError("vllm.image_variants must include cu129")
    for name, variant in variants.items():
        if not isinstance(variant, Mapping):
            raise ProbeConfigError(f"image variant {name} must be a mapping")
        if not DIGEST_REF_RE.fullmatch(str(variant.get("base_image", ""))):
            raise ProbeConfigError(f"image variant {name}: base_image must be pinned by digest")
        if not IMAGE_ID_RE.fullmatch(str(variant.get("base_image_id", ""))):
            raise ProbeConfigError(f"image variant {name}: base_image_id must be sha256:<64 hex>")
        env = variant.get("env", {})
        if not isinstance(env, Mapping) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in env.items()
        ):
            raise ProbeConfigError(f"image variant {name}: env must map strings to strings")

    seeds = raw.get("primary_seeds")
    if (
        not isinstance(seeds, list)
        or len(seeds) < 3
        or len(set(seeds)) != len(seeds)
        or not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
    ):
        raise ProbeConfigError("primary_seeds must list at least three distinct integers")

    for section in ("gates", "validity", "dummy_admissibility", "stop", "sampling", "server"):
        if not isinstance(raw.get(section), Mapping):
            raise ProbeConfigError(f"config section {section!r} is missing")
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
        if not ID_RE.fullmatch(str(engine_id)) or not isinstance(entry, Mapping):
            raise ProbeConfigError(f"engine {engine_id!r} is malformed")
        mode = entry.get("mode")
        if mode not in {"server", "offline"}:
            raise ProbeConfigError(f"engine {engine_id}: mode must be server or offline")
        model = entry.get("model")
        if model not in models:
            raise ProbeConfigError(f"engine {engine_id}: unknown model {model!r}")
        load_format = entry.get("load_format")
        if load_format not in {"auto", "dummy"}:
            raise ProbeConfigError(f"engine {engine_id}: load_format must be auto or dummy")
        if load_format == "auto" and models[model]["weights"] != "real":
            raise ProbeConfigError(f"engine {engine_id}: real weights need a real-weight model")
        if models[model]["weights"] == "admission-token":
            raise ProbeConfigError(f"engine {engine_id}: an admission token is never served")
        flags = _validate_flags(str(engine_id), entry.get("flags"))
        if mode == "offline" and "limit_mm_per_prompt" in flags:
            raise ProbeConfigError(f"engine {engine_id}: the offline engine is text-only")
        engines[str(engine_id)] = EngineSpec(str(engine_id), mode, model, load_format, flags)

    raw_points = raw.get("points")
    if not isinstance(raw_points, Mapping) or not raw_points:
        raise ProbeConfigError("points must be a non-empty mapping")
    points = {
        str(point_id): _validate_point(str(point_id), entry)
        for point_id, entry in raw_points.items()
    }
    for point in points.values():
        control = point.get("control_of")
        if control is not None and control not in points:
            raise ProbeConfigError(f"point {point.point_id}: control_of names unknown {control!r}")

    raw_jobs = raw.get("jobs")
    if not isinstance(raw_jobs, Mapping) or not raw_jobs:
        raise ProbeConfigError("jobs must be a non-empty mapping")
    jobs: dict[str, JobSpec] = {}
    for job_id, entry in raw_jobs.items():
        jobs[str(job_id)] = _validate_job(str(job_id), entry, models, engines, points)

    return ProbeConfig(
        path=path,
        sha256=sha256,
        raw=raw,
        primary_seeds=tuple(seeds),
        models=models,
        engines=engines,
        points=points,
        jobs=jobs,
    )


def _validate_job(
    job_id: str,
    entry: Any,
    models: Mapping[str, Mapping[str, Any]],
    engines: Mapping[str, EngineSpec],
    points: Mapping[str, PointSpec],
) -> JobSpec:
    if not re.fullmatch(r"[a-z]", job_id) or not isinstance(entry, Mapping):
        raise ProbeConfigError(f"job {job_id!r} is malformed")
    allocation = _positive_int(entry.get("allocation_minutes"), f"job {job_id}.allocation_minutes")
    lane_model = entry.get("lane_model")
    if lane_model not in models or models[lane_model]["weights"] not in {"real", "admission-token"}:
        raise ProbeConfigError(f"job {job_id}: lane_model must be a receipted real-weight model")
    raw_phases = entry.get("phases")
    if not isinstance(raw_phases, list) or not raw_phases:
        raise ProbeConfigError(f"job {job_id}: phases must be a non-empty list")
    seen_points: set[str] = set()
    phases: list[PhaseSpec] = []
    total_reserve = 0.0
    for phase in raw_phases:
        if not isinstance(phase, Mapping) or not ID_RE.fullmatch(str(phase.get("id", ""))):
            raise ProbeConfigError(f"job {job_id}: phase id is malformed")
        engine_id = phase.get("engine")
        if engine_id not in engines:
            raise ProbeConfigError(f"job {job_id}: unknown engine {engine_id!r}")
        engine = engines[engine_id]
        if engine.load_format == "auto" and engine.model != lane_model:
            raise ProbeConfigError(
                f"job {job_id}: real weights must be the lane-verified model {lane_model}"
            )
        point_ids = phase.get("points")
        if not isinstance(point_ids, list) or not point_ids:
            raise ProbeConfigError(f"job {job_id}: phase {phase['id']} has no points")
        resolved: list[PointSpec] = []
        for point_id in point_ids:
            if point_id not in points:
                raise ProbeConfigError(f"job {job_id}: unknown point {point_id!r}")
            if point_id in seen_points:
                raise ProbeConfigError(f"job {job_id}: point {point_id} is scheduled twice")
            seen_points.add(point_id)
            point = points[point_id]
            allowed = SERVER_KINDS if engine.mode == "server" else OFFLINE_KINDS
            if point.kind not in allowed:
                raise ProbeConfigError(
                    f"job {job_id}: point {point_id} ({point.kind}) cannot run on {engine.mode}"
                )
            resolved.append(point)
        first_kind = resolved[0].kind
        if first_kind not in {"smoke-server", "smoke-offline"}:
            raise ProbeConfigError(f"job {job_id}: phase {phase['id']} must start with its smoke")
        reserve = _positive_number(
            phase.get("reserve_minutes", 0),
            f"{job_id}.{phase['id']}.reserve_minutes",
            allow_zero=True,
        )
        total_reserve += reserve
        phases.append(
            PhaseSpec(
                phase_id=str(phase["id"]),
                engine=engine,
                role=str(phase.get("role", "primary")),
                reserve_minutes=reserve,
                points=tuple(resolved),
            )
        )
    if total_reserve >= allocation:
        raise ProbeConfigError(f"job {job_id}: phase reserves exceed the allocation")
    job = JobSpec(
        job_id=job_id,
        title=str(entry.get("title", "")),
        allocation_minutes=allocation,
        lane_model=str(lane_model),
        phases=tuple(phases),
    )
    _ = job.mode  # a job never mixes server and offline engines
    return job


def load_config(path: Path) -> ProbeConfig:
    """Read, hash and validate the probe contract."""
    data = path.read_bytes()
    try:
        raw = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise ProbeConfigError(f"config is not valid YAML: {exc}") from exc
    return validate_config(raw, path=path, sha256=hashlib.sha256(data).hexdigest())


def bind_seeds(config: ProbeConfig, seeds: Sequence[int]) -> tuple[int, ...]:
    """Check that the executed ``--seeds`` equal the declared primary seeds exactly."""
    executed = tuple(int(seed) for seed in seeds)
    if executed != config.primary_seeds:
        raise ProbeConfigError(
            f"--seeds {list(executed)} differ from the contract's primary seeds "
            f"{list(config.primary_seeds)}"
        )
    return executed


def parse_weight_pins(values: Sequence[str]) -> dict[str, tuple[str, str]]:
    """Parse ``MODEL_ID=RECEIPT_SHA256:ARTIFACT_ROOT_SHA256`` pins."""
    pins: dict[str, tuple[str, str]] = {}
    for value in values:
        model_id, separator, digests = value.partition("=")
        receipt, colon, root = digests.partition(":")
        if (
            not separator
            or not colon
            or not MODEL_ID_RE.fullmatch(model_id)
            or not SHA_RE.fullmatch(receipt)
            or not SHA_RE.fullmatch(root)
        ):
            raise ProbeConfigError(
                f"weight pin {value!r} must be MODEL_ID=RECEIPT_SHA256:ARTIFACT_ROOT_SHA256"
            )
        if model_id in pins:
            raise ProbeConfigError(f"weight pin for {model_id} is repeated")
        pins[model_id] = (receipt, root)
    return pins


def check_pins(job: JobSpec, pins: Mapping[str, tuple[str, str]]) -> None:
    """Every dummy-weight model outside the lane binding needs exactly one pin."""
    required = set(job.pinned_models())
    if set(pins) != required:
        raise ProbeConfigError(
            f"job {job.job_id} needs weight pins for {sorted(required)}, got {sorted(pins)}"
        )
