"""Fail-closed contract for managed LoRA experiments executed through Tinker."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OCI_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}$")


class TinkerContractError(ValueError):
    """Raised when a Tinker experiment contract cannot be trusted or executed."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TinkerPrices(StrictModel):
    prefill_per_million: float = Field(ge=0)
    sample_per_million: float = Field(ge=0)
    train_per_million: float = Field(ge=0)
    verified_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    source: str = Field(pattern=r"^https://")

    @model_validator(mode="after")
    def finite_prices(self) -> Self:
        values = (
            self.prefill_per_million,
            self.sample_per_million,
            self.train_per_million,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Tinker prices must be finite")
        return self


class TinkerStage(StrictModel):
    name: str = Field(pattern=SLUG_RE.pattern)
    role: Literal["smoke", "target", "control"]
    tinker_id: str = Field(min_length=3)
    context_tokens: int = Field(gt=0)
    train_tokens_per_seed: int = Field(ge=0)
    sample_tokens_per_seed: int = Field(ge=0)
    prefill_tokens_per_seed: int = Field(ge=0)
    prices: TinkerPrices

    def cost_per_seed(self) -> float:
        return (
            self.train_tokens_per_seed * self.prices.train_per_million
            + self.sample_tokens_per_seed * self.prices.sample_per_million
            + self.prefill_tokens_per_seed * self.prices.prefill_per_million
        ) / 1_000_000


class LoraPolicy(StrictModel):
    rank: int = Field(ge=1, le=256)
    learning_rate: float = Field(gt=0, le=0.1)
    batch_size: int = Field(ge=1, le=1024)
    max_steps: int = Field(ge=1)
    train_mlp: bool
    train_attn: bool
    train_unembed: bool

    @model_validator(mode="after")
    def finite_learning_rate(self) -> Self:
        if not math.isfinite(self.learning_rate):
            raise ValueError("learning_rate must be finite")
        if not any((self.train_mlp, self.train_attn, self.train_unembed)):
            raise ValueError("at least one LoRA component must be trainable")
        return self


class DataSplit(StrictModel):
    source: str = Field(min_length=3)
    identity: str = Field(min_length=10)
    sha256: str | None = None
    sealed: bool = False

    @model_validator(mode="after")
    def valid_hash(self) -> Self:
        if self.sha256 is not None and not SHA256_RE.fullmatch(self.sha256):
            raise ValueError("split sha256 must contain 64 lowercase hexadecimal characters")
        return self


class TinkerData(StrictModel):
    record_schema: Literal["rendered-prefix-target-v1"]
    renderer_identity: str = Field(min_length=10)
    train: DataSplit | None = None
    train_by_arm: dict[str, DataSplit] | None = None
    development: DataSplit
    test: DataSplit
    contamination_checks: tuple[str, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def sealed_test(self) -> Self:
        if not self.test.sealed:
            raise ValueError("test split must be sealed")
        if (self.train is None) == (self.train_by_arm is None):
            raise ValueError("provide exactly one of data.train or data.train_by_arm")
        if self.train_by_arm is not None:
            if not self.train_by_arm:
                raise ValueError("data.train_by_arm cannot be empty")
            if any(not SLUG_RE.fullmatch(name) for name in self.train_by_arm):
                raise ValueError("data.train_by_arm keys must be arm slugs")
        return self


class ExperimentArm(StrictModel):
    name: str = Field(pattern=SLUG_RE.pattern)
    lora: bool
    purpose: str = Field(min_length=15)
    capsule: bool | None = None
    prompt_policy: bool | None = None
    native_host_policy: bool | None = None
    label_source: Literal[
        "none", "causal_holdout", "next_use", "observational_utility"
    ] | None = None
    controller_runtime: Literal["none", "frozen_external", "model_emitted"] | None = None


class CheckpointPolicy(StrictModel):
    full_state_every_steps: int = Field(ge=1)
    sampler_weights_every_steps: int = Field(ge=1)
    periodic_ttl_seconds: int = Field(ge=3600)
    durable_ttl_seconds: int = Field(ge=24 * 3600)
    retain_minimum_generations: int = Field(ge=2)
    resume_with_optimizer: Literal[True]
    download_final_weights: Literal[True]
    keep_local_cursor_and_rng: Literal[True]
    fresh_client_resume_test: Literal[True]


class TinkerBudget(StrictModel):
    max_usd: float = Field(gt=0)
    max_client_minutes: int = Field(ge=1, le=24 * 60)
    max_checkpoint_storage_gb_month: float = Field(ge=0)
    storage_per_gb_month: float = Field(ge=0)

    @model_validator(mode="after")
    def finite_budget(self) -> Self:
        values = (
            self.max_usd,
            self.max_checkpoint_storage_gb_month,
            self.storage_per_gb_month,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Tinker budget values must be finite")
        return self


class TinkerExecution(StrictModel):
    enabled: bool
    client_runtime: Literal["slurm-cpu-container"]
    sdk_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    secret_env: Literal["TINKER_API_KEY"]
    container_image: str | None = None
    command_argv: tuple[str, ...] | None = None
    capability_receipt_sha256: str | None = None
    blocked_by: tuple[str, ...] = ()

    @model_validator(mode="after")
    def executable_provenance(self) -> Self:
        if self.container_image is not None and not OCI_RE.fullmatch(self.container_image):
            raise ValueError("container_image must contain an immutable OCI digest")
        if self.capability_receipt_sha256 is not None and not SHA256_RE.fullmatch(
            self.capability_receipt_sha256
        ):
            raise ValueError("capability receipt must be a SHA-256 digest")
        if self.enabled:
            if self.container_image is None:
                raise ValueError("enabled Tinker runs require a digest-pinned container")
            if not self.command_argv or not all(self.command_argv):
                raise ValueError("enabled Tinker runs require command_argv")
            if self.capability_receipt_sha256 is None:
                raise ValueError("enabled Tinker runs require an online capability receipt")
            if self.blocked_by:
                raise ValueError("enabled Tinker runs cannot retain blockers")
        elif not self.blocked_by:
            raise ValueError("disabled Tinker runs must state blockers")
        return self


class PrimaryEndpoint(StrictModel):
    metric: str = Field(min_length=10)
    direction: Literal["maximize", "minimize"]
    minimum_effect: float = Field(gt=0)
    unit_of_analysis: str = Field(min_length=10)
    safety_gate: str = Field(min_length=10)


class TinkerExperimentContract(StrictModel):
    schema_version: Literal[1]
    name: str = Field(pattern=SLUG_RE.pattern)
    status: Literal["contract", "pilot-ready"]
    experiment_kind: Literal["portable_capsule", "causal_memory_policy"]
    research_question: str = Field(min_length=40)
    null_hypothesis: str = Field(min_length=30)
    portability_claim: str = Field(min_length=30)
    stages: tuple[TinkerStage, ...] = Field(min_length=2)
    lora: LoraPolicy
    seeds: tuple[int, ...] = Field(min_length=3)
    data: TinkerData
    arms: tuple[ExperimentArm, ...] = Field(min_length=4)
    controls: tuple[str, ...] = Field(min_length=3)
    primary_endpoint: PrimaryEndpoint
    falsifiers: tuple[str, ...] = Field(min_length=3)
    checkpoints: CheckpointPolicy
    budget: TinkerBudget
    execution: TinkerExecution
    required_artifacts: tuple[str, ...] = Field(min_length=6)

    @model_validator(mode="after")
    def internal_consistency(self) -> Self:
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("seeds must be distinct")
        if not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in self.seeds):
            raise ValueError("seeds must be integers")
        stage_names = [stage.name for stage in self.stages]
        if len(set(stage_names)) != len(stage_names):
            raise ValueError("stage names must be distinct")
        roles = {stage.role for stage in self.stages}
        if not {"smoke", "target"}.issubset(roles):
            raise ValueError("Tinker ladder requires smoke and target stages")
        arm_names = [arm.name for arm in self.arms]
        if len(set(arm_names)) != len(arm_names):
            raise ValueError("arm names must be distinct")
        if self.experiment_kind == "portable_capsule":
            if not all(
                arm.capsule is not None
                and arm.prompt_policy is not None
                and arm.native_host_policy is not None
                for arm in self.arms
            ):
                raise ValueError("portable capsule arms require capsule policy fields")
            if not any(arm.capsule and arm.lora for arm in self.arms):
                raise ValueError("at least one arm must combine a capsule with LoRA")
            if not any(not arm.capsule and not arm.lora for arm in self.arms):
                raise ValueError("at least one arm must be an unmodified-base control")
            if self.data.train is None:
                raise ValueError("portable capsule experiments require data.train")
        else:
            if not all(
                arm.label_source is not None and arm.controller_runtime is not None
                for arm in self.arms
            ):
                raise ValueError(
                    "causal memory arms require label_source and controller_runtime"
                )
            learned_labels = {
                arm.label_source for arm in self.arms if arm.lora
            }
            required_labels = {"causal_holdout", "next_use", "observational_utility"}
            if not required_labels.issubset(learned_labels):
                raise ValueError("causal memory requires three matched learned label arms")
            if not any(
                not arm.lora
                and arm.label_source == "none"
                and arm.controller_runtime == "none"
                for arm in self.arms
            ):
                raise ValueError("causal memory requires an unmodified base control")
            expected_train_arms = {arm.name for arm in self.arms if arm.lora}
            if self.data.train_by_arm is None or set(self.data.train_by_arm) != expected_train_arms:
                raise ValueError("data.train_by_arm must exactly match LoRA arm names")
        if self.cost_ceiling_usd() > self.budget.max_usd + 1e-9:
            raise ValueError(
                f"declared Tinker token ceiling costs ${self.cost_ceiling_usd():.4f}, "
                f"above max_usd ${self.budget.max_usd:.4f}"
            )
        if self.execution.enabled:
            train_splits = (
                {"train": self.data.train}
                if self.data.train is not None
                else self.data.train_by_arm or {}
            )
            all_splits = {
                **train_splits,
                "development": self.data.development,
                "test": self.data.test,
            }
            for split_name, split in all_splits.items():
                if split is None or split.sha256 is None:
                    raise ValueError(f"enabled Tinker runs require data.{split_name}.sha256")
        if self.status == "pilot-ready" and not self.execution.enabled:
            raise ValueError("pilot-ready Tinker contracts must be enabled")
        return self

    def cost_ceiling_usd(self) -> float:
        trainable_arms = (
            sum(arm.lora for arm in self.arms)
            if self.experiment_kind == "causal_memory_policy"
            else 1
        )
        token_cost = (
            len(self.seeds)
            * trainable_arms
            * sum(stage.cost_per_seed() for stage in self.stages)
        )
        storage_cost = (
            self.budget.max_checkpoint_storage_gb_month
            * self.budget.storage_per_gb_month
        )
        return token_cost + storage_cost


def load_tinker_contract(path: Path) -> TinkerExperimentContract:
    """Load a YAML contract while presenting validation failures as domain errors."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        return TinkerExperimentContract.model_validate(payload)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        raise TinkerContractError(str(exc)) from exc
