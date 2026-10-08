"""Shared interfaces for the Q2 evaluator-mutation study (binding).

This module is owned by the harness branch (``stage0/q2-mut-harness``). The
spec and operator branches copy it verbatim; a change here is a new schema
version, never a silent edit. It is standard-library only so it can run in the
OSWorld metric container, the LibreOffice container and the repository venv.

Four record types cross branch boundaries:

``SanitizedTask``
    What the blind requirement-spec author may see about one OSWorld task:
    the instruction, the apps, the initial files and the snapshot name. It
    never carries an evaluator, expected file, result getter, postconfig,
    metric name or option. ``FORBIDDEN_TASK_KEYS`` is checked recursively.

``RequirementSpec``
    Atomic requirements written from the sanitized task only, by an author
    that has never seen checker code or probe output. Stored as YAML under
    ``program/evidence/q2-mutation/specs/<task_id>.yaml``.

``MutationResult``
    One deterministic, seeded mutant produced by an operator, with its label
    fixed a priori from the requirement spec (``witness``), never from a
    checker verdict.

``VerdictRow``
    One checker verdict on one candidate end state, written as a JSONL row by
    the harness after the GUI-faithful LibreOffice save.

Every ``from_dict`` is strict: unknown keys, missing keys and wrong types raise
``SchemaError``. Never coerce a malformed record into a result.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = "q2-mutation-schema-v1"

# --- sanitized task -------------------------------------------------------

SANITIZED_TASK_KEYS: tuple[str, ...] = (
    "task_id",
    "domain",
    "instruction",
    "related_apps",
    "initial_files",
    "snapshot",
)
INITIAL_FILE_KEYS: tuple[str, ...] = ("url", "path_in_vm", "sha256")

# Keys that reveal how a task is scored. None may appear at any depth of a
# sanitized task. "hint", "source" and "trajectory" are excluded as well:
# they are not part of the instruction an agent sees.
FORBIDDEN_TASK_KEYS: frozenset[str] = frozenset(
    {
        "evaluator",
        "expected",
        "result",
        "postconfig",
        "metric",
        "metrics",
        "func",
        "options",
        "rules",
        "conj",
        "hint",
        "source",
        "trajectory",
        "gold",
    }
)

# --- requirement spec -----------------------------------------------------

SPEC_AUTHOR = "blind-model-author-v1"
CHECK_KINDS: tuple[str, ...] = (
    "cell_value",
    "cell_format",
    "text_run",
    "paragraph_format",
    "slide_object",
    "table_cell",
    "file_exists",
    "config_value",
    "image_property",
    "other",
)
SPEC_KEYS: tuple[str, ...] = ("task_id", "author", "requirements", "allowed_variations")
REQUIREMENT_KEYS: tuple[str, ...] = ("req_id", "statement", "check_kind", "observable")

# --- mutation result ------------------------------------------------------

LABELS: tuple[str, ...] = (
    "should_pass_equiv",
    "should_pass_alt_solution",
    "should_fail_violation",
    "should_fail_extra_change",
    "ambiguous",
)
SHOULD_PASS_LABELS: frozenset[str] = frozenset({"should_pass_equiv", "should_pass_alt_solution"})
SHOULD_FAIL_LABELS: frozenset[str] = frozenset(
    {"should_fail_violation", "should_fail_extra_change"}
)
# A mutant built through the application's document model and saved by the
# pinned LibreOffice is "document_model". A byte-level edit that no GUI save
# can produce (split runs, re-packed zips, re-serialized XML) belongs to the
# separate "script_writer" stratum and is never pooled with the headline.
STRATA: tuple[str, ...] = ("document_model", "script_writer")
MUTATION_KEYS: tuple[str, ...] = (
    "mutant_id",
    "task_id",
    "operator",
    "family",
    "label",
    "witness",
    "purity_checks",
    "recipe",
)
MUTATION_OPTIONAL_KEYS: tuple[str, ...] = (
    "stratum",
    "target_path_in_vm",
    "output_sha256",
    "schema_version",
)
WITNESS_KEYS: tuple[str, ...] = ("req_ids", "argument")
PURITY_CHECK_KEYS: tuple[str, ...] = ("name", "passed", "detail")
RECIPE_REQUIRED_KEYS: tuple[str, ...] = ("seed", "input_sha256", "params")

# --- verdict row ----------------------------------------------------------

VERDICTS: tuple[str, ...] = ("pass", "fail", "error")
SAVED_VIA: tuple[str, ...] = ("gui_faithful_lo_save", "none")
VERDICT_KEYS: tuple[str, ...] = (
    "mutant_id",
    "task_id",
    "checker_funcs",
    "score",
    "verdict",
    "saved_via",
    "lo_build",
    "venv_lock_sha256",
    "seconds",
)
VERDICT_OPTIONAL_KEYS: tuple[str, ...] = (
    "error",
    "dep_set",
    "candidate_sha256",
    "scored_sha256",
    "harness_revision",
    "conj",
    "schema_version",
)
# pass means score == 1.0 exactly (the preregistered checker-verdict rule);
# graded partial credit is a fail for verdict purposes and is kept in "score".
PASS_SCORE = 1.0

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TASK_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_REQ_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class SchemaError(ValueError):
    """Raised when a record does not match the binding Q2 mutation schema."""


# --- helpers --------------------------------------------------------------


def canonical_json(obj: Any) -> str:
    """Deterministic JSON text (sorted keys, no whitespace, no NaN)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def recipe_sha256(recipe: Mapping[str, Any]) -> str:
    """SHA-256 of a recipe's canonical JSON; the recipe's identity."""
    return sha256_text(canonical_json(dict(recipe)))


def make_mutant_id(task_id: str, operator: str, recipe: Mapping[str, Any]) -> str:
    """Deterministic mutant id: ``<task_id>__<operator>__<recipe hash 12>``."""
    _require_task_id(task_id, "task_id")
    _require_slug(operator, "operator")
    return f"{task_id}__{operator}__{recipe_sha256(recipe)[:12]}"


def verdict_for_score(score: float | None) -> str:
    """Map an ``evaluate()`` score to a verdict; ``None`` means it raised."""
    if score is None:
        return "error"
    if not isinstance(score, int | float) or isinstance(score, bool) or not math.isfinite(score):
        raise SchemaError(f"score must be a finite number, got {score!r}")
    return "pass" if float(score) >= PASS_SCORE else "fail"


def _require_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaError(f"{where}: expected an object, got {type(value).__name__}")
    return value


def _require_exact_keys(
    value: Mapping[str, Any],
    required: Sequence[str],
    where: str,
    optional: Sequence[str] = (),
) -> None:
    keys = set(value)
    missing = [key for key in required if key not in keys]
    unknown = sorted(keys - set(required) - set(optional))
    if missing:
        raise SchemaError(f"{where}: missing keys {missing}")
    if unknown:
        raise SchemaError(f"{where}: unknown keys {unknown}")


def _require_str(value: Any, where: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise SchemaError(f"{where}: expected a string, got {type(value).__name__}")
    if not allow_empty and not value.strip():
        raise SchemaError(f"{where}: must be non-empty")
    return value


def _require_str_list(value: Any, where: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise SchemaError(f"{where}: expected a list, got {type(value).__name__}")
    if not allow_empty and not value:
        raise SchemaError(f"{where}: must be non-empty")
    return [_require_str(item, f"{where}[{i}]") for i, item in enumerate(value)]


def _require_sha256(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SchemaError(f"{where}: expected 64 lowercase hex characters")
    return value


def _require_task_id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _TASK_ID_RE.fullmatch(value):
        raise SchemaError(f"{where}: expected an OSWorld task UUID, got {value!r}")
    return value


def _require_slug(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _SLUG_RE.fullmatch(value):
        raise SchemaError(f"{where}: expected a short identifier, got {value!r}")
    return value


def _require_choice(value: Any, choices: Iterable[str], where: str) -> str:
    options = tuple(choices)
    if value not in options:
        raise SchemaError(f"{where}: {value!r} not in {list(options)}")
    return str(value)


def find_forbidden_keys(obj: Any, path: str = "$") -> list[str]:
    """Return JSON paths of every forbidden key at any depth of ``obj``."""
    hits: list[str] = []
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            here = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_TASK_KEYS:
                hits.append(here)
            hits.extend(find_forbidden_keys(value, here))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            hits.extend(find_forbidden_keys(value, f"{path}[{index}]"))
    return hits


# --- sanitized task -------------------------------------------------------


@dataclass(frozen=True)
class InitialFile:
    url: str
    path_in_vm: str
    sha256: str

    @classmethod
    def from_dict(cls, data: Any, where: str = "initial_file") -> InitialFile:
        mapping = _require_mapping(data, where)
        _require_exact_keys(mapping, INITIAL_FILE_KEYS, where)
        url = _require_str(mapping["url"], f"{where}.url")
        if not url.startswith("https://"):
            raise SchemaError(f"{where}.url: expected an https URL")
        path = _require_str(mapping["path_in_vm"], f"{where}.path_in_vm")
        if not path.startswith("/"):
            raise SchemaError(f"{where}.path_in_vm: expected an absolute VM path")
        return cls(url=url, path_in_vm=path, sha256=_require_sha256(mapping["sha256"], where))

    def to_dict(self) -> dict[str, str]:
        return {"url": self.url, "path_in_vm": self.path_in_vm, "sha256": self.sha256}


@dataclass(frozen=True)
class SanitizedTask:
    task_id: str
    domain: str
    instruction: str
    related_apps: tuple[str, ...]
    initial_files: tuple[InitialFile, ...]
    snapshot: str

    @classmethod
    def from_dict(cls, data: Any) -> SanitizedTask:
        mapping = _require_mapping(data, "sanitized_task")
        hits = find_forbidden_keys(mapping)
        if hits:
            raise SchemaError(f"sanitized_task: forbidden evaluator-like keys at {hits}")
        _require_exact_keys(mapping, SANITIZED_TASK_KEYS, "sanitized_task")
        files = mapping["initial_files"]
        if not isinstance(files, list):
            raise SchemaError("sanitized_task.initial_files: expected a list")
        return cls(
            task_id=_require_task_id(mapping["task_id"], "sanitized_task.task_id"),
            domain=_require_slug(mapping["domain"], "sanitized_task.domain"),
            instruction=_require_str(mapping["instruction"], "sanitized_task.instruction"),
            related_apps=tuple(
                _require_str_list(mapping["related_apps"], "sanitized_task.related_apps")
            ),
            initial_files=tuple(
                InitialFile.from_dict(item, f"sanitized_task.initial_files[{i}]")
                for i, item in enumerate(files)
            ),
            snapshot=_require_str(mapping["snapshot"], "sanitized_task.snapshot"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "domain": self.domain,
            "instruction": self.instruction,
            "related_apps": list(self.related_apps),
            "initial_files": [item.to_dict() for item in self.initial_files],
            "snapshot": self.snapshot,
        }


# --- requirement spec -----------------------------------------------------


@dataclass(frozen=True)
class Requirement:
    req_id: str
    statement: str
    check_kind: str
    observable: str

    @classmethod
    def from_dict(cls, data: Any, where: str = "requirement") -> Requirement:
        mapping = _require_mapping(data, where)
        _require_exact_keys(mapping, REQUIREMENT_KEYS, where)
        req_id = mapping["req_id"]
        if not isinstance(req_id, str) or not _REQ_ID_RE.fullmatch(req_id):
            raise SchemaError(f"{where}.req_id: expected a short identifier, got {req_id!r}")
        return cls(
            req_id=req_id,
            statement=_require_str(mapping["statement"], f"{where}.statement"),
            check_kind=_require_choice(mapping["check_kind"], CHECK_KINDS, f"{where}.check_kind"),
            observable=_require_str(mapping["observable"], f"{where}.observable"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "req_id": self.req_id,
            "statement": self.statement,
            "check_kind": self.check_kind,
            "observable": self.observable,
        }


@dataclass(frozen=True)
class RequirementSpec:
    task_id: str
    author: str
    requirements: tuple[Requirement, ...]
    allowed_variations: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Any) -> RequirementSpec:
        mapping = _require_mapping(data, "spec")
        _require_exact_keys(mapping, SPEC_KEYS, "spec")
        author = _require_choice(mapping["author"], (SPEC_AUTHOR,), "spec.author")
        raw_reqs = mapping["requirements"]
        if not isinstance(raw_reqs, list) or not raw_reqs:
            raise SchemaError("spec.requirements: expected a non-empty list")
        reqs = tuple(
            Requirement.from_dict(item, f"spec.requirements[{i}]")
            for i, item in enumerate(raw_reqs)
        )
        ids = [req.req_id for req in reqs]
        if len(set(ids)) != len(ids):
            raise SchemaError("spec.requirements: duplicate req_id")
        return cls(
            task_id=_require_task_id(mapping["task_id"], "spec.task_id"),
            author=author,
            requirements=reqs,
            allowed_variations=tuple(
                _require_str_list(mapping["allowed_variations"], "spec.allowed_variations")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "author": self.author,
            "requirements": [req.to_dict() for req in self.requirements],
            "allowed_variations": list(self.allowed_variations),
        }

    def req_ids(self) -> frozenset[str]:
        return frozenset(req.req_id for req in self.requirements)


# --- mutation result ------------------------------------------------------


@dataclass(frozen=True)
class Witness:
    """How a label follows from the spec, independently of any checker.

    ``req_ids`` names the requirements the mutant violates (should_fail_violation,
    at least one) or provably preserves; ``argument`` is the reasoning.
    """

    req_ids: tuple[str, ...]
    argument: str

    @classmethod
    def from_dict(cls, data: Any, where: str = "witness") -> Witness:
        mapping = _require_mapping(data, where)
        _require_exact_keys(mapping, WITNESS_KEYS, where)
        return cls(
            req_ids=tuple(_require_str_list(mapping["req_ids"], f"{where}.req_ids")),
            argument=_require_str(mapping["argument"], f"{where}.argument"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"req_ids": list(self.req_ids), "argument": self.argument}


@dataclass(frozen=True)
class PurityCheck:
    name: str
    passed: bool
    detail: str

    @classmethod
    def from_dict(cls, data: Any, where: str = "purity_check") -> PurityCheck:
        mapping = _require_mapping(data, where)
        _require_exact_keys(mapping, PURITY_CHECK_KEYS, where)
        if not isinstance(mapping["passed"], bool):
            raise SchemaError(f"{where}.passed: expected a boolean")
        return cls(
            name=_require_slug(mapping["name"], f"{where}.name"),
            passed=mapping["passed"],
            detail=_require_str(mapping["detail"], f"{where}.detail", allow_empty=True),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _validate_recipe(value: Any, where: str = "recipe") -> dict[str, Any]:
    mapping = dict(_require_mapping(value, where))
    missing = [key for key in RECIPE_REQUIRED_KEYS if key not in mapping]
    if missing:
        raise SchemaError(f"{where}: missing keys {missing}")
    seed = mapping["seed"]
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise SchemaError(f"{where}.seed: expected an integer")
    _require_sha256(mapping["input_sha256"], f"{where}.input_sha256")
    _require_mapping(mapping["params"], f"{where}.params")
    try:
        canonical_json(mapping)
    except (TypeError, ValueError) as exc:
        raise SchemaError(f"{where}: not canonical-JSON serializable ({exc})") from exc
    return mapping


@dataclass(frozen=True)
class MutationResult:
    mutant_id: str
    task_id: str
    operator: str
    family: str
    label: str
    witness: Witness
    purity_checks: tuple[PurityCheck, ...]
    recipe: dict[str, Any]
    stratum: str = "document_model"
    target_path_in_vm: str | None = None
    output_sha256: str | None = None
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def from_dict(cls, data: Any) -> MutationResult:
        mapping = _require_mapping(data, "mutation")
        _require_exact_keys(mapping, MUTATION_KEYS, "mutation", MUTATION_OPTIONAL_KEYS)
        task_id = _require_task_id(mapping["task_id"], "mutation.task_id")
        operator = _require_slug(mapping["operator"], "mutation.operator")
        recipe = _validate_recipe(mapping["recipe"], "mutation.recipe")
        mutant_id = _require_str(mapping["mutant_id"], "mutation.mutant_id")
        if mutant_id != make_mutant_id(task_id, operator, recipe):
            raise SchemaError("mutation.mutant_id: does not match make_mutant_id(recipe)")
        label = _require_choice(mapping["label"], LABELS, "mutation.label")
        witness = Witness.from_dict(mapping["witness"], "mutation.witness")
        if label == "should_fail_violation" and not witness.req_ids:
            raise SchemaError("mutation.witness: should_fail_violation must name a req_id")
        checks = mapping["purity_checks"]
        if not isinstance(checks, list):
            raise SchemaError("mutation.purity_checks: expected a list")
        target = mapping.get("target_path_in_vm")
        if target is not None:
            _require_str(target, "mutation.target_path_in_vm")
            if not target.startswith("/"):
                raise SchemaError("mutation.target_path_in_vm: expected an absolute VM path")
        output = mapping.get("output_sha256")
        if output is not None:
            _require_sha256(output, "mutation.output_sha256")
        version = mapping.get("schema_version", SCHEMA_VERSION)
        _require_choice(version, (SCHEMA_VERSION,), "mutation.schema_version")
        return cls(
            mutant_id=mutant_id,
            task_id=task_id,
            operator=operator,
            family=_require_slug(mapping["family"], "mutation.family"),
            label=label,
            witness=witness,
            purity_checks=tuple(
                PurityCheck.from_dict(item, f"mutation.purity_checks[{i}]")
                for i, item in enumerate(checks)
            ),
            recipe=recipe,
            stratum=_require_choice(
                mapping.get("stratum", "document_model"), STRATA, "mutation.stratum"
            ),
            target_path_in_vm=target,
            output_sha256=output,
            schema_version=version,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "mutant_id": self.mutant_id,
            "task_id": self.task_id,
            "operator": self.operator,
            "family": self.family,
            "label": self.label,
            "witness": self.witness.to_dict(),
            "purity_checks": [check.to_dict() for check in self.purity_checks],
            "recipe": dict(self.recipe),
            "stratum": self.stratum,
            "schema_version": self.schema_version,
        }
        if self.target_path_in_vm is not None:
            out["target_path_in_vm"] = self.target_path_in_vm
        if self.output_sha256 is not None:
            out["output_sha256"] = self.output_sha256
        return out

    def check_against_spec(self, spec: RequirementSpec) -> None:
        """Every req_id in the witness must exist in the task's spec."""
        if spec.task_id != self.task_id:
            raise SchemaError("mutation and spec are for different tasks")
        unknown = sorted(set(self.witness.req_ids) - spec.req_ids())
        if unknown:
            raise SchemaError(f"mutation.witness: req_ids {unknown} are not in the spec")


# --- verdict row ----------------------------------------------------------


@dataclass(frozen=True)
class VerdictRow:
    mutant_id: str
    task_id: str
    checker_funcs: tuple[str, ...]
    score: float | None
    verdict: str
    saved_via: str
    lo_build: str | None
    venv_lock_sha256: str
    seconds: float
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Any) -> VerdictRow:
        mapping = _require_mapping(data, "verdict")
        _require_exact_keys(mapping, VERDICT_KEYS, "verdict", VERDICT_OPTIONAL_KEYS)
        score = mapping["score"]
        if score is not None and (
            isinstance(score, bool)
            or not isinstance(score, int | float)
            or not math.isfinite(score)
        ):
            raise SchemaError("verdict.score: expected a finite number or null")
        verdict = _require_choice(mapping["verdict"], VERDICTS, "verdict.verdict")
        if verdict != verdict_for_score(score):
            raise SchemaError(
                f"verdict.verdict: {verdict!r} contradicts score {score!r} "
                f"(pass iff score >= {PASS_SCORE}; error iff score is null)"
            )
        saved_via = _require_choice(mapping["saved_via"], SAVED_VIA, "verdict.saved_via")
        lo_build = mapping["lo_build"]
        if saved_via == "gui_faithful_lo_save" or lo_build is not None:
            _require_str(lo_build, "verdict.lo_build")
        seconds = mapping["seconds"]
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, int | float)
            or not math.isfinite(seconds)
            or seconds < 0
        ):
            raise SchemaError("verdict.seconds: expected a non-negative number")
        extras = {key: mapping[key] for key in VERDICT_OPTIONAL_KEYS if key in mapping}
        if verdict == "error":
            _require_str(extras.get("error"), "verdict.error (required when verdict is error)")
        for key in ("candidate_sha256", "scored_sha256"):
            if key in extras and extras[key] is not None:
                _require_sha256(extras[key], f"verdict.{key}")
        return cls(
            mutant_id=_require_str(mapping["mutant_id"], "verdict.mutant_id"),
            task_id=_require_task_id(mapping["task_id"], "verdict.task_id"),
            checker_funcs=tuple(
                _require_str_list(
                    mapping["checker_funcs"], "verdict.checker_funcs", allow_empty=False
                )
            ),
            score=None if score is None else float(score),
            verdict=verdict,
            saved_via=saved_via,
            lo_build=lo_build,
            venv_lock_sha256=_require_sha256(
                mapping["venv_lock_sha256"], "verdict.venv_lock_sha256"
            ),
            seconds=float(seconds),
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "mutant_id": self.mutant_id,
            "task_id": self.task_id,
            "checker_funcs": list(self.checker_funcs),
            "score": self.score,
            "verdict": self.verdict,
            "saved_via": self.saved_via,
            "lo_build": self.lo_build,
            "venv_lock_sha256": self.venv_lock_sha256,
            "seconds": self.seconds,
        }
        out.update(self.extras)
        return out

    def to_jsonl(self) -> str:
        return canonical_json(self.to_dict())


def read_verdict_rows(lines: Iterable[str]) -> list[VerdictRow]:
    """Parse JSONL verdict rows strictly; blank lines are skipped."""
    rows: list[VerdictRow] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SchemaError(f"verdict line {number}: invalid JSON ({exc})") from exc
        try:
            rows.append(VerdictRow.from_dict(payload))
        except SchemaError as exc:
            raise SchemaError(f"verdict line {number}: {exc}") from exc
    return rows
