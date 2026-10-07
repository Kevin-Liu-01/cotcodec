from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.exec_research_workload import check_model_mount
from scripts.submit_docker_research_job import (
    BATCH_SCRIPT,
    FOREIGN_GPU_PROCESS_EXIT_CODE,
    RUNTIME,
    sbatch_argv,
    validate_manifest,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = PROJECT_ROOT / "infra" / "research" / "Dockerfile"
SOURCE_OVERLAY_DOCKERFILE = (
    PROJECT_ROOT / "infra" / "research" / "Dockerfile.source-overlay"
)
SOURCE_OVERLAY_BUILDER = PROJECT_ROOT / "scripts" / "build_source_overlay_on_h100.sh"


def test_research_image_accepts_normal_json_argv() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert 'ENTRYPOINT ["/bin/bash", "-lc"]' not in content
    assert 'CMD ["python", "scripts/check_harness_env.py"]' in content


def test_research_image_dev_dependencies_are_explicit_and_default_off() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert "ARG INCLUDE_DEV=false" in content
    assert 'org.opencontainers.image.cotcodec-dev-dependencies="${INCLUDE_DEV}"' in content
    assert 'if [ "${INCLUDE_DEV}" = "true" ]; then dev_flag="--dev"' in content


def test_source_overlay_records_profile_and_dev_dependency_contract() -> None:
    content = SOURCE_OVERLAY_DOCKERFILE.read_text(encoding="utf-8")
    assert "ARG UV_EXTRA=architecture" in content
    assert "ARG INCLUDE_DEV=false" in content
    assert "ARG GIT_TREE=unknown" in content
    assert 'cotcodec-git-sha="${GIT_SHA}"' in content
    assert 'cotcodec-git-tree="${GIT_TREE}"' in content
    assert 'cotcodec-runtime-profile="${UV_EXTRA}-source-overlay"' in content
    assert 'cotcodec-dev-dependencies="${INCLUDE_DEV}"' in content
    assert 'if [ "${INCLUDE_DEV}" = "true" ]; then dev_flag="--dev"' in content
    assert 'if [ "${UV_EXTRA}" = "none" ]; then' in content
    assert 'uv sync --frozen "${dev_flag}" --extra "${UV_EXTRA}"' in content
    assert "find /workspace/cotcodec -mindepth 1 -maxdepth 1" in content
    assert "! -name .venv -exec rm -rf -- {} +" in content
    assert "cotcodec-source-overlay-venv" not in content
    assert "COPY . /workspace/cotcodec" in content


def test_overlay_builders_make_normalized_archive_readable_to_container_uid() -> None:
    for path in (SOURCE_OVERLAY_BUILDER,):
        content = path.read_text(encoding="utf-8")
        assert '${SLURM_JOB_ID:?Run this build through Slurm}' in content
        assert 'chmod -R a+rX "${context}"' in content
        assert "sudo" not in content


def test_source_overlay_builder_refuses_stale_context_and_validates_receipt() -> None:
    content = SOURCE_OVERLAY_BUILDER.read_text(encoding="utf-8")
    assert '${COTCODEC_SOURCE_RECEIPT:?Set the retained source receipt path}' in content
    assert '${COTCODEC_SOURCE_EXTRACTOR:?Set the retained source extractor path}' in content
    assert '${COTCODEC_SOURCE_EXTRACTOR_SHA256:?' in content
    assert '${COTCODEC_SOURCE_BUILDER_SHA256:?' in content
    assert "refusing to reuse source-overlay build root" in content
    assert 'python3 "${extractor_snapshot}"' in content
    assert 'BASE_IMAGE=${COTCODEC_BASE_IMAGE_TAG}' in content
    assert '@sha256:[0-9a-f]{64}' in content
    assert "--pull=false" in content
    assert 'tar -xzf "${COTCODEC_SOURCE_ARCHIVE}"' not in content


@pytest.mark.parametrize("drifted_input", ["builder", "extractor"])
def test_source_overlay_builder_rejects_unbound_helpers(
    tmp_path: Path, drifted_input: str
) -> None:
    extractor = tmp_path / "extractor.py"
    extractor.write_text("raise SystemExit(99)\n", encoding="utf-8")
    builder_sha256 = hashlib.sha256(SOURCE_OVERLAY_BUILDER.read_bytes()).hexdigest()
    extractor_sha256 = hashlib.sha256(extractor.read_bytes()).hexdigest()
    if drifted_input == "builder":
        builder_sha256 = "0" * 64
    else:
        extractor_sha256 = "0" * 64
    env = {
        **os.environ,
        "SLURM_JOB_ID": "123",
        "COTCODEC_SOURCE_ARCHIVE": str(tmp_path / "source.tar.gz"),
        "COTCODEC_SOURCE_RECEIPT": str(tmp_path / "source.json"),
        "COTCODEC_SOURCE_EXTRACTOR": str(extractor),
        "COTCODEC_SOURCE_EXTRACTOR_SHA256": extractor_sha256,
        "COTCODEC_SOURCE_BUILDER_SHA256": builder_sha256,
        "COTCODEC_SOURCE_SHA256": "1" * 64,
        "COTCODEC_GIT_SHA": "2" * 40,
        "COTCODEC_GIT_TREE": "3" * 40,
        "COTCODEC_BASE_IMAGE_TAG": "local.invalid/base@sha256:" + "5" * 64,
        "COTCODEC_BASE_IMAGE_ID": "sha256:" + "4" * 64,
        "COTCODEC_BUILD_ROOT": str(tmp_path / "build"),
    }
    result = subprocess.run(
        ["bash", str(SOURCE_OVERLAY_BUILDER)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "builder or extractor digest mismatch" in result.stderr


# ---------------------------------------------------------------------------
# docker-research.sbatch runtime contract
#
# Admission re-checks run before any Linux-only step, so they execute on every
# platform. The full-run tests replace docker, nvidia-smi and scontrol with
# stubs and need GNU stat/date, /proc and bash >= 4.4; they run on Linux only.
# ---------------------------------------------------------------------------

ARCHIVED_PREFIX = "memory workloads were archived under legacy/"
DIGEST_STAGE = "batch script digest does not match the submitted manifest"
NO_MODEL_REASON = "CPU doctor on an H100 allocation needs no checkpoint"
ARCHIVE_MASK = "/workspace/cotcodec/legacy:ro,noexec,nosuid,nodev,size=64k"
SHARED_GPU_REASON = "co-scheduled profiler measures contention on purpose"
CHECKPOINT_SCRIPT = (
    "python scripts/verify_compute_provenance.py > /outputs/provenance-verification.txt"
    " && bash scripts/check_compute_env.sh container > /outputs/container-doctor.txt"
    " && python scripts/fetch_open_model.py --model-root /model-cache/cotcodec-models"
    ' --receipt-root /model-cache/cotcodec-receipts verify "$COTCODEC_MODEL_ID"'
    " > /outputs/model-verification.txt && exec python scripts/exec_research_workload.py"
)
NO_MODEL_SCRIPT = (
    "python scripts/verify_compute_provenance.py > /outputs/provenance-verification.txt"
    " && bash scripts/check_compute_env.sh container > /outputs/container-doctor.txt"
    " && exec python scripts/exec_research_workload.py"
)
RUNTIME_SKIP = pytest.mark.skipif(
    not sys.platform.startswith("linux") or shutil.which("bash") is None,
    reason="the stubbed batch run needs Linux /proc, GNU stat and date, and bash >= 4.4",
)


def _seeded_raw(run_root: str = "/home/kevin/cotcodec-runs/lane") -> dict:
    return {
        "runtime": RUNTIME,
        "name": "lane-check",
        "image_id": "sha256:" + "a" * 64,
        "command": ["python", "scripts/probe.py", "--seeds", "42", "43", "44"],
        "run_root": run_root,
        "git_sha": "b" * 40,
        "source_sha256": "c" * 64,
        "model": {
            "cache_host_path": "/home/kevin/cotcodec-runs/hf-cache",
            "model_id": "qwen3.5-4b",
            "revision": "d" * 40,
            "receipt_sha256": "e" * 64,
            "artifact_root_sha256": "f" * 64,
        },
        "seeds": [42, 43, 44],
        "seed_binding": {"flag": "--seeds"},
        "resources": {"gpu_type": "h100", "gpus": 1, "cpus": 8, "memory_gb": 32, "minutes": 30},
        "budget": {"max_gpu_hours": 0.5},
    }


def _deterministic_raw(**kwargs: str) -> dict:
    raw = _seeded_raw(**kwargs)
    raw["randomness_contract"] = "deterministic"
    raw["seeds"] = []
    del raw["seed_binding"]
    raw["command"] = ["python", "scripts/probe.py"]
    return raw


def _batch_env(manifest: dict) -> dict[str, str]:
    argument = next(
        value for value in sbatch_argv(manifest, test_only=True) if value.startswith("--export=")
    )
    env = dict(item.split("=", 1) for item in argument.removeprefix("--export=").split(","))
    env.update(
        {
            "PATH": os.pathsep.join(
                [str(Path(sys.executable).parent), "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
            ),
            "SLURM_JOB_ID": "4242",
            "SLURM_JOB_NODELIST": "fal-h100-01",
            "SLURM_MEM_PER_NODE": str(manifest["memory_gb"] * 1024),
            "CUDA_VISIBLE_DEVICES": "0",
        }
    )
    return env


def _rewrite(env: dict[str, str], *, command: list[str] | None = None, **fields) -> None:
    """Change the exported manifest (and command) consistently, as a forger would."""

    manifest = json.loads(bytes.fromhex(env["COTCODEC_MANIFEST_JSON_HEX"]))
    if command is not None:
        manifest["command"] = command
        env["COTCODEC_COMMAND_JSON_HEX"] = json.dumps(command, separators=(",", ":")).encode().hex()
    for key, value in fields.items():
        if value is None:
            manifest.pop(key, None)
        else:
            manifest[key] = value
    env["COTCODEC_MANIFEST_JSON_HEX"] = (
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode().hex()
    )


def _admit(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run the batch script with a wrong digest so it stops after admission."""

    return subprocess.run(
        ["bash", str(BATCH_SCRIPT)],
        env={**env, "COTCODEC_BATCH_SHA256": "0" * 64},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _assert_admitted(env: dict[str, str]) -> None:
    result = _admit(env)
    assert result.returncode == 2, result.stderr
    assert DIGEST_STAGE in result.stderr, result.stderr


def _assert_refused(env: dict[str, str], message: str) -> None:
    result = _admit(env)
    assert result.returncode != 0, result.stderr
    assert DIGEST_STAGE not in result.stderr
    assert message in result.stderr, result.stderr


admission_only = pytest.mark.skipif(
    shutil.which("sha256sum", path="/usr/bin:/bin:/usr/sbin:/sbin") is None,
    reason="the batch digest stage needs sha256sum",
)


@admission_only
@pytest.mark.parametrize(
    "variant",
    [
        "seeded",
        "deterministic",
        "deterministic-all-serve",
        "profile-default",
        "profile-vllm",
        "profile-large-cpu-mem",
        "no-model",
        "shared-gpu",
        "gpu-memory-utilization",
        "assignment-seeds",
    ],
)
def test_batch_admits_every_valid_submitter_output(variant: str) -> None:
    raw = _deterministic_raw() if variant.startswith("deterministic") else _seeded_raw()
    if variant == "deterministic-all-serve":
        raw["randomness_contract"] = variant
    if variant.startswith("profile-"):
        raw["container_profile"] = variant.removeprefix("profile-")
    if variant == "no-model":
        raw["model"] = {"kind": "none", "reason": NO_MODEL_REASON}
    if variant == "shared-gpu":
        raw["allow_shared_gpu"] = True
        raw["shared_gpu_reason"] = SHARED_GPU_REASON
    if variant == "gpu-memory-utilization":
        raw["command"] += ["--gpu-memory-utilization", "0.9"]
    if variant == "assignment-seeds":
        raw["seed_binding"] = {"flag": "--assignment-seeds"}
        raw["command"][2] = "--assignment-seeds"
    _assert_admitted(_batch_env(validate_manifest(raw)))


@admission_only
@pytest.mark.parametrize(
    "element",
    [
        "scripts/run_memory_model_screen.py",
        "scripts/run_letta_baseline.py",
        "harness.memory_trials.runner",
        "--memory-treatment-mode",
        "--expected-memory-system-id=memgpt",
        "--memory-bund",
    ],
)
def test_batch_rejects_archived_memory_argv(element: str) -> None:
    env = _batch_env(validate_manifest(_deterministic_raw()))
    _rewrite(env, command=["python", "scripts/probe.py", element])
    _assert_refused(env, ARCHIVED_PREFIX)


# Commands that the submitters and the batch script all admitted on 5ed577d. A
# forger who bypasses the submitter must still be stopped by the batch script.
REVIEW_BYPASS_COMMANDS = [
    ["python", "-mlegacy.scripts.run_memory_model_screen", "--output-dir", "/outputs/x"],
    ["python", "-mharness.memory_trials"],
    ["env", "PYTHONPATH=legacy/scripts", "python", "-m", "run_memory_model_screen"],
    ["env", "--chdir=legacy/scripts", "python", "run_memory_trials.py"],
    ["python", "-c", "from legacy.harness import memory_trials"],
    ["python", "legacy/scripts/run_memorybank_decay_container.py", "--output", "/outputs/x"],
    ["python", "-m", "legacy.harness.causal_memory_trials"],
    ["python", "legacy/scripts/run_memgpt_letta_lifecycle_doctor.py"],
]


@admission_only
@pytest.mark.parametrize("command", REVIEW_BYPASS_COMMANDS)
def test_batch_rejects_review_bypass_commands(command: list[str]) -> None:
    raw = _deterministic_raw()
    raw["command"] = command
    with pytest.raises(ValueError, match=f"^{ARCHIVED_PREFIX}"):
        validate_manifest(raw)
    env = _batch_env(validate_manifest(_deterministic_raw()))
    _rewrite(env, command=command)
    _assert_refused(env, ARCHIVED_PREFIX)


@admission_only
def test_batch_rejects_memory_inputs() -> None:
    env = _batch_env(validate_manifest(_deterministic_raw()))
    env["COTCODEC_MEMORY_BUNDLE_SHA256"] = "1" * 64
    _assert_refused(env, ARCHIVED_PREFIX)
    env = _batch_env(validate_manifest(_deterministic_raw()))
    _rewrite(env, memory_bundle={"sha256": "1" * 64})
    _assert_refused(env, ARCHIVED_PREFIX)


@admission_only
def test_batch_rechecks_seed_binding() -> None:
    manifest = validate_manifest(_seeded_raw())

    env = _batch_env(manifest)
    del env["COTCODEC_SEED_BINDING_FLAG"]
    _assert_refused(env, "seed binding differs from the manifest")

    env = _batch_env(manifest)
    del env["COTCODEC_SEED_BINDING_FLAG"]
    _rewrite(env, seed_binding=None)
    _assert_refused(env, "declared seeds require a registered seed binding flag")

    env = _batch_env(manifest)
    _rewrite(env, command=["python", "scripts/probe.py", "--seeds", "43", "42", "44"])
    _assert_refused(env, "executed seeds do not exactly match declared seeds")

    env = _batch_env(manifest)
    _rewrite(
        env, command=["python", "scripts/probe.py", "--seeds", "42", "43", "44", "--seed", "1"]
    )
    _assert_refused(env, "does not execute declared seeds via exactly one --seeds")

    env = _batch_env(manifest)
    env["COTCODEC_SEEDS"] = "42:43:45"
    _assert_refused(env, "declared seeds differ from the manifest")

    env = _batch_env(validate_manifest(_deterministic_raw()))
    _rewrite(env, command=["python", "scripts/probe.py", "--seed", "0"])
    _assert_refused(env, "deterministic jobs cannot execute seed options")


@admission_only
@pytest.mark.parametrize("abbreviation", [["--see", "7"], ["--see=7"], ["--assign", "7"]])
def test_batch_rejects_seed_option_abbreviations(abbreviation: list[str]) -> None:
    # The review case: argparse would turn the trailing --see 7 into --seeds 7.
    raw = _seeded_raw()
    raw["command"] = [
        "python",
        "scripts/run_translation_supervised_indexer_doctor.py",
        "--output",
        "/outputs/r.json",
        "--seeds",
        "42",
        "43",
        "44",
    ]
    env = _batch_env(validate_manifest(raw))
    _rewrite(env, command=raw["command"] + abbreviation)
    _assert_refused(env, "seed options must be spelled in full")

    env = _batch_env(validate_manifest(_deterministic_raw()))
    _rewrite(env, command=["python", "scripts/probe.py", *abbreviation])
    _assert_refused(env, "seed options must be spelled in full")


@admission_only
@pytest.mark.parametrize("value", ["gpu-heavy", "", "VLLM"])
def test_batch_rejects_unknown_container_profiles(value: str) -> None:
    env = _batch_env(validate_manifest(_seeded_raw()))
    env["COTCODEC_CONTAINER_PROFILE"] = value
    _assert_refused(env, "COTCODEC_CONTAINER_PROFILE is not a registered container profile")


@admission_only
def test_batch_rejects_a_profile_the_manifest_did_not_declare() -> None:
    env = _batch_env(validate_manifest(_seeded_raw()))
    env["COTCODEC_CONTAINER_PROFILE"] = "vllm"
    _assert_refused(env, "container profile differs from the manifest")


@admission_only
def test_batch_requires_the_slurm_memory_limit_to_equal_memory_gb() -> None:
    env = _batch_env(validate_manifest(_seeded_raw()))
    del env["SLURM_MEM_PER_NODE"]
    _assert_refused(env, "did not export SLURM_MEM_PER_NODE")
    env = _batch_env(validate_manifest(_seeded_raw()))
    env["SLURM_MEM_PER_NODE"] = "65536"
    _assert_refused(env, "SLURM_MEM_PER_NODE differs from the manifest memory_gb")


@admission_only
def test_batch_admits_no_model_only_through_the_explicit_kind() -> None:
    raw = _seeded_raw()
    raw["model"] = {"kind": "none", "reason": NO_MODEL_REASON}
    no_model = _batch_env(validate_manifest(raw))

    env = dict(no_model, COTCODEC_MODEL_REVISION="d" * 40)
    _assert_refused(env, "a no-model job sets COTCODEC_MODEL_ID=none")

    env = dict(no_model, COTCODEC_MODEL_KIND="checkpoint")
    _assert_refused(env, "COTCODEC_MODEL_KIND may only be none")

    env = dict(no_model)
    del env["COTCODEC_MODEL_KIND"]
    _assert_refused(env, "COTCODEC_MODEL_CACHE_HOST_HEX")

    checkpoint = _batch_env(validate_manifest(_seeded_raw()))
    env = dict(checkpoint, COTCODEC_MODEL_ID="none")
    _assert_refused(env, "COTCODEC_MODEL_ID=none requires COTCODEC_MODEL_KIND=none")

    env = {
        key: value
        for key, value in checkpoint.items()
        if not key.startswith("COTCODEC_MODEL_")
    }
    env.update(COTCODEC_MODEL_KIND="none", COTCODEC_MODEL_ID="none")
    _assert_refused(env, "no-model admission differs from the manifest")


@admission_only
def test_batch_shared_gpu_flag_must_match_the_manifest() -> None:
    env = _batch_env(validate_manifest(_seeded_raw()))
    env["COTCODEC_ALLOW_SHARED_GPU"] = "true"
    _assert_refused(env, "shared-GPU admission differs from the manifest")
    env["COTCODEC_ALLOW_SHARED_GPU"] = "yes"
    _assert_refused(env, "COTCODEC_ALLOW_SHARED_GPU may only be true")


def test_batch_forwards_signals_while_the_workload_runs() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert 'docker start --attach "${container_name}" &' in content
    assert 'wait "${docker_client_pid}" || wait_status=$?' in content
    forward = content.split("forward_signal() {", 1)[1].split("\n}\n", 1)[0]
    # The snapshot follows the running check (a docker inspect) and precedes the
    # signal, so a periodic save that lands during the inspect is part of it.
    running = forward.index("if ! container_running; then")
    snapshot = forward.index('marker_before="$(checkpoint_marker_identity)"')
    clock = forward.index('requested_ns="$(date +%s%N)"')
    kill = forward.index('docker kill --signal "${signal_name}"')
    assert running < snapshot < clock < kill
    assert (
        'checkpoint_marker_is_fresh "${marker_before}" "${requested_ns}" "${signal_name}"'
        in forward
    )
    assert "signal_checkpoint_confirmed=true" in forward
    assert '[[ ! -f "${checkpoint_marker}"' not in forward
    fresh = content.split("checkpoint_marker_is_fresh() {", 1)[1].split("\n}\n", 1)[0]
    assert '"trigger=SIG${signal_name}"' in fresh
    termination = content.split("write_termination() {", 1)[1].split("\n}\n", 1)[0]
    assert 'echo "checkpoint_ready=${signal_checkpoint_confirmed}"' in termination


def test_batch_prolog_checks_allocated_gpus_before_docker_create() -> None:
    content = BATCH_SCRIPT.read_text(encoding="utf-8")
    assert FOREIGN_GPU_PROCESS_EXIT_CODE == 75
    assert "foreign_gpu_process_exit_code=75" in content
    assert content.index("count_foreign_gpu_processes)") < content.index("docker create \\")
    assert "--query-compute-apps=gpu_uuid,pid,process_name,used_memory" in content
    assert 'exit "${foreign_gpu_process_exit_code}"' in content


def test_no_model_container_refuses_a_visible_model_cache(tmp_path: Path) -> None:
    cache = tmp_path / "model-cache"
    check_model_mount({"COTCODEC_MODEL_ID": "none"}, cache)
    check_model_mount({"COTCODEC_MODEL_ID": "qwen3.5-4b"}, cache)
    cache.mkdir()
    check_model_mount({"COTCODEC_MODEL_ID": "qwen3.5-4b"}, cache)
    check_model_mount({}, cache)
    with pytest.raises(SystemExit, match="model cache is mounted"):
        check_model_mount({"COTCODEC_MODEL_ID": "none"}, cache)


# --- stubbed full runs (Linux) -----------------------------------------------

FAKE_DOCKER = r"""#!/usr/bin/env bash
set -u
state="${FAKE_DOCKER_STATE:?}"
python -c 'import json, sys; print(json.dumps(sys.argv[1:]))' "$@" >> "${state}/calls.jsonl"
case "$1" in
  info|version) echo "fake docker"; exit 0 ;;
  image)
    if [[ "$3" == --format ]]; then
      case "$4" in
        *revision*) echo "${COTCODEC_GIT_SHA}" ;;
        *source-tree-sha256*) echo "${COTCODEC_SOURCE_SHA256}" ;;
        *) echo "$5" ;;
      esac
    else
      echo '[]'
    fi
    exit 0 ;;
  create) echo created > "${state}/status"; echo fake-container-id; exit 0 ;;
  inspect)
    status="$(cat "${state}/status" 2>/dev/null || echo missing)"
    if [[ "$2" == --format ]]; then
      case "$3" in
        '{{.State.Running}}')
          # A periodic save that finishes during this inspect (review case A).
          if [[ "${FAKE_PERIODIC_SAVE_ON_INSPECT:-false}" == true && "${status}" == running ]]; then
            saves="$(( $(cat "${state}/periodic-saves" 2>/dev/null || echo 0) + 1 ))"
            echo "${saves}" > "${state}/periodic-saves"
            printf 'step=periodic-%s\n' "${saves}" > "${FAKE_RUN_DIR}/checkpoint.ready.tmp"
            mv "${FAKE_RUN_DIR}/checkpoint.ready.tmp" "${FAKE_RUN_DIR}/checkpoint.ready"
          fi
          if [[ "${status}" == running ]]; then echo true; else echo false; fi ;;
        *) echo "${status} $(cat "${state}/exit_code" 2>/dev/null || echo 0)" ;;
      esac
    else
      echo '[]'
    fi
    exit 0 ;;
  start) exec bash "${FAKE_WORKLOAD}" ;;
  kill) kill -s "$3" "$(cat "${state}/workload.pid")"; exit 0 ;;
  rm)
    if [[ "$(cat "${state}/status" 2>/dev/null)" == running ]]; then
      kill -9 "$(cat "${state}/workload.pid")" 2>/dev/null || true
    fi
    exit 0 ;;
  logs) exit 0 ;;
esac
echo "unexpected docker call: $*" >&2
exit 99
"""

FAKE_WORKLOAD = r"""#!/usr/bin/env bash
set -u
state="${FAKE_DOCKER_STATE:?}"
marker="${FAKE_RUN_DIR:?}/checkpoint.ready"
finish() {
  echo "$1" > "${state}/exit_code"
  echo exited > "${state}/status"
  exit "$1"
}
write_marker() {
  printf '%s\n' "$@" > "${marker}.tmp"
  mv "${marker}.tmp" "${marker}"
}
on_usr1() {
  echo USR1 >> "${state}/workload-signals"
  # Finish the save even if the batch script's TERM arrives meanwhile.
  trap '' TERM
  case "${FAKE_WORKLOAD_MODE}" in
    checkpoint-on-signal) write_marker trigger=SIGUSR1 step=signal-checkpoint ;;
    untriggered-on-signal) write_marker step=signal-checkpoint ;;
    wrong-trigger-on-signal) write_marker trigger=SIGTERM ;;
    periodic-after-signal)
      # Review case B: a periodic save lands after the signal, and the
      # workload stops without its own signal-triggered save.
      ( sleep 0.5; write_marker step=periodic-1000 ) &
      sleep 1.5 ;;
  esac
  finish 0
}
trap on_usr1 USR1
trap 'echo TERM >> "${state}/workload-signals"; finish 143' TERM
echo running > "${state}/status"
case "${FAKE_PERIODIC_MARKER:-false}" in
  true) write_marker step=periodic-checkpoint ;;
  stale-trigger) write_marker trigger=SIGUSR1 step=stale ;;
esac
echo "$$" > "${state}/workload.pid.tmp"
mv "${state}/workload.pid.tmp" "${state}/workload.pid"
case "${FAKE_WORKLOAD_MODE}" in
  exit-*) finish "${FAKE_WORKLOAD_MODE#exit-}" ;;
esac
while :; do sleep 0.05; done
"""

FAKE_NVIDIA_SMI = r"""#!/usr/bin/env bash
devices=""
query=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i) devices="$2"; shift 2 ;;
    --query-gpu=*) query="gpu:${1#--query-gpu=}"; shift ;;
    --query-compute-apps=*) query=apps; shift ;;
    *) shift ;;
  esac
done
case "${query}" in
  apps)
    if [[ -n "${FAKE_COMPUTE_APPS:-}" ]]; then printf '%s\n' "${FAKE_COMPUTE_APPS}"; fi
    exit "${FAKE_COMPUTE_APPS_STATUS:-0}" ;;
  gpu:name) for d in ${devices//,/ }; do echo "NVIDIA H100 80GB HBM3"; done ;;
  gpu:uuid) for d in ${devices//,/ }; do printf 'GPU-00000000-0000-0000-0000-%012d\n' "$d"; done ;;
  *) for d in ${devices//,/ }; do echo "$d, NVIDIA H100 80GB HBM3, GPU-x, 81559 MiB"; done ;;
esac
"""


def _gpu_uuid(index: int) -> str:
    return f"GPU-00000000-0000-0000-0000-{index:012d}"


class StubbedRun:
    """One docker-research.sbatch execution against stub host tools."""

    def __init__(self, root: Path, raw: dict, **fake_env: str) -> None:
        self.root = root
        self.state = root / "docker-state"
        self.state.mkdir()
        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name, body in (
            ("docker", FAKE_DOCKER),
            ("nvidia-smi", FAKE_NVIDIA_SMI),
            ("scontrol", "#!/usr/bin/env bash\necho \"JobId=$3\"\n"),
        ):
            (bin_dir / name).write_text(body, encoding="utf-8")
            (bin_dir / name).chmod(0o755)
        workload = root / "workload.sh"
        workload.write_text(FAKE_WORKLOAD, encoding="utf-8")
        self.cache = root / "model-cache"
        if "kind" not in raw["model"]:
            receipt = {
                "model_id": raw["model"]["model_id"],
                "revision": raw["model"]["revision"],
                "artifact_root_sha256": raw["model"]["artifact_root_sha256"],
                "mode": "full",
                "publication_eligible": True,
                "trust_remote_code": False,
            }
            (self.cache / "cotcodec-models" / raw["model"]["model_id"]).mkdir(parents=True)
            receipts = self.cache / "cotcodec-receipts"
            receipts.mkdir()
            receipt_path = receipts / f"{raw['model']['model_id']}.json"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            raw["model"]["cache_host_path"] = str(self.cache)
            raw["model"]["receipt_sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        raw["run_root"] = str(root / "runs")
        self.manifest = validate_manifest(raw)
        self.run_dir = root / "runs" / "4242"
        self.env = _batch_env(self.manifest)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{self.env['PATH']}"
        self.env.update(
            {
                "FAKE_DOCKER_STATE": str(self.state),
                "FAKE_WORKLOAD": str(workload),
                "FAKE_RUN_DIR": str(self.run_dir),
                "FAKE_WORKLOAD_MODE": "exit-0",
                **fake_env,
            }
        )
        self.process: subprocess.Popen[bytes] | None = None

    def start(self) -> None:
        self.stdout = (self.root / "stdout.txt").open("wb")
        self.stderr_path = self.root / "stderr.txt"
        self.stderr = self.stderr_path.open("wb")
        self.process = subprocess.Popen(
            ["bash", str(BATCH_SCRIPT)],
            env=self.env,
            stdout=self.stdout,
            stderr=self.stderr,
        )

    def wait_for_workload(self, timeout: float = 30) -> None:
        deadline = time.monotonic() + timeout
        while not (self.state / "workload.pid").exists():
            assert self.process is not None and self.process.poll() is None, self.stderr_text()
            assert time.monotonic() < deadline, "the fake workload never started"
            time.sleep(0.05)

    def finish(self, timeout: float = 60) -> int:
        assert self.process is not None
        try:
            return self.process.wait(timeout=timeout)
        finally:
            if self.process.poll() is None:
                self.process.kill()
            pid_file = self.state / "workload.pid"
            if pid_file.exists():
                with contextlib.suppress(ProcessLookupError, ValueError):
                    os.kill(int(pid_file.read_text()), signal.SIGKILL)
            self.stdout.close()
            self.stderr.close()

    def run(self) -> int:
        self.start()
        return self.finish()

    def stderr_text(self) -> str:
        return self.stderr_path.read_text(encoding="utf-8", errors="replace")

    def calls(self, subcommand: str) -> list[list[str]]:
        path = self.state / "calls.jsonl"
        if not path.exists():
            return []
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        return [row for row in rows if row and row[0] == subcommand]

    def create_args(self) -> list[str]:
        (args,) = self.calls("create")
        return args

    def env_file(self, name: str) -> dict[str, str]:
        text = (self.run_dir / name).read_text(encoding="utf-8")
        return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


@pytest.fixture
def lane_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # A fresh directory whose path satisfies the submitter's simple-path rule.
    return tmp_path_factory.mktemp("lane")


def _cpu_list() -> str:
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("Cpus_allowed_list:"):
            return line.split()[1]
    raise AssertionError("Cpus_allowed_list is missing")


@RUNTIME_SKIP
def test_default_manifest_runs_with_the_original_container_flags(lane_root: Path) -> None:
    run = StubbedRun(lane_root, _deterministic_raw())
    assert run.run() == 0, run.stderr_text()
    env = run.env
    expected = [
        "create",
        "--name", "cotcodec-4242",
        "--entrypoint", "/bin/bash",
        "--gpus", "device=0",
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=8g",
        "--tmpfs", ARCHIVE_MASK,
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", "4096",
        "--cpuset-cpus", _cpu_list(),
        "--memory", "32768m",
        "--memory-swap", "32768m",
        "--ulimit", "core=0",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--workdir", "/workspace/cotcodec",
        "--env", f"COTCODEC_COMMAND_JSON_HEX={env['COTCODEC_COMMAND_JSON_HEX']}",
        "--env", f"COTCODEC_GIT_SHA={env['COTCODEC_GIT_SHA']}",
        "--env", f"COTCODEC_SOURCE_SHA256={env['COTCODEC_SOURCE_SHA256']}",
        "--env", "COTCODEC_EXPECTED_GPUS=1",
        "--env", "COTCODEC_OUTPUT_DIR=/outputs",
        "--env", "COTCODEC_CHECKPOINT_MARKER=/outputs/checkpoint.ready",
        "--env", "COTCODEC_MODEL_ID=qwen3.5-4b",
        "--env", "USER=cotcodec",
        "--env", "LOGNAME=cotcodec",
        "--env", "HOME=/tmp/home",
        "--env", "XDG_CACHE_HOME=/tmp/cache",
        "--env", "TORCH_HOME=/tmp/torch",
        "--env", "TORCHINDUCTOR_CACHE_DIR=/tmp/torchinductor",
        "--env", "CUBLAS_WORKSPACE_CONFIG=:4096:8",
        "--env", "HF_HUB_OFFLINE=1",
        "--env", "TRANSFORMERS_OFFLINE=1",
        "--env", "HF_HOME=/tmp/huggingface",
        "--env", "PYTHONUNBUFFERED=1",
        "--volume", f"{run.run_dir}:/outputs:rw",
        "--volume", f"{run.cache}:/model-cache:ro",
        "sha256:" + "a" * 64,
        "-lc", CHECKPOINT_SCRIPT,
    ]  # fmt: skip
    assert run.create_args() == expected
    job = run.env_file("job.env")
    assert job["model_kind"] == "checkpoint"
    assert job["container_profile"] == "default"
    assert job["allow_shared_gpu"] == "false"
    assert job["memory_limit_mb"] == "32768"
    assert run.env_file("gpu-prolog.env")["decision"] == "exclusive"
    termination = run.env_file("termination.env")
    assert termination["reason"] == "completed"
    assert termination["exit_code"] == "0"
    assert (run.run_dir / "model-receipt.json").is_file()


@RUNTIME_SKIP
def test_workload_exit_code_is_propagated(lane_root: Path) -> None:
    run = StubbedRun(lane_root, _deterministic_raw(), FAKE_WORKLOAD_MODE="exit-3")
    assert run.run() == 3, run.stderr_text()
    assert run.env_file("termination.env")["reason"] == "workload_failed"


@RUNTIME_SKIP
@pytest.mark.parametrize(
    ("profile", "tmpfs", "shm", "pids"),
    [
        ("default", "/tmp:rw,nosuid,nodev,size=8g", None, "4096"),
        ("vllm", "/tmp:rw,exec,nosuid,nodev,size=32g", "16g", "8192"),
        ("large-cpu-mem", "/tmp:rw,exec,nosuid,nodev,size=8g", None, "4096"),
    ],
)
def test_container_profile_selects_docker_flags(
    lane_root: Path, profile: str, tmpfs: str, shm: str | None, pids: str
) -> None:
    raw = _seeded_raw()
    raw["container_profile"] = profile
    run = StubbedRun(lane_root, raw)
    assert run.run() == 0, run.stderr_text()
    args = run.create_args()
    tmpfs_at = args.index("--tmpfs")
    assert args[tmpfs_at + 1] == tmpfs
    if shm is None:
        assert "--shm-size" not in args
        assert args[tmpfs_at + 2 : tmpfs_at + 5] == ["--tmpfs", ARCHIVE_MASK, "--cap-drop"]
    else:
        assert args[tmpfs_at + 2 : tmpfs_at + 6] == ["--shm-size", shm, "--tmpfs", ARCHIVE_MASK]
    assert args[args.index("--pids-limit") + 1] == pids
    assert run.env_file("job.env")["container_profile"] == profile


@RUNTIME_SKIP
def test_docker_memory_limit_equals_manifest_memory(lane_root: Path) -> None:
    raw = _seeded_raw()
    raw["resources"]["memory_gb"] = 48
    run = StubbedRun(lane_root, raw)
    assert run.run() == 0, run.stderr_text()
    args = run.create_args()
    assert args[args.index("--memory") + 1] == "49152m"
    assert args[args.index("--memory-swap") + 1] == "49152m"


@RUNTIME_SKIP
def test_no_model_job_mounts_no_cache_and_skips_receipt_verification(lane_root: Path) -> None:
    raw = _seeded_raw()
    raw["model"] = {"kind": "none", "reason": NO_MODEL_REASON}
    run = StubbedRun(lane_root, raw)
    assert run.run() == 0, run.stderr_text()
    args = run.create_args()
    assert not any(value.endswith(":/model-cache:ro") for value in args)
    assert "COTCODEC_MODEL_ID=none" in args
    assert args[-2:] == ["-lc", NO_MODEL_SCRIPT]
    job = run.env_file("job.env")
    assert job["model_kind"] == "none"
    assert job["model_id"] == "none"
    assert job["model_revision"] == "none"
    assert job["model_receipt_sha256"] == "none"
    assert not (run.run_dir / "model-receipt.json").exists()


@RUNTIME_SKIP
def test_foreign_gpu_process_refuses_the_job_with_a_distinct_exit_code(lane_root: Path) -> None:
    run = StubbedRun(
        lane_root,
        _seeded_raw(),
        FAKE_COMPUTE_APPS=f"{_gpu_uuid(0)}, 31337, python, 2048 MiB",
    )
    assert run.run() == FOREIGN_GPU_PROCESS_EXIT_CODE, run.stderr_text()
    assert "foreign compute process" in run.stderr_text()
    assert run.calls("create") == []
    assert run.env_file("gpu-prolog.env")["decision"] == "refused"
    termination = run.env_file("termination.env")
    assert termination["reason"] == "foreign_gpu_process"
    assert termination["exit_code"] == str(FOREIGN_GPU_PROCESS_EXIT_CODE)


@RUNTIME_SKIP
def test_processes_on_unallocated_gpus_do_not_block_the_job(lane_root: Path) -> None:
    run = StubbedRun(
        lane_root,
        _seeded_raw(),
        FAKE_COMPUTE_APPS=f"{_gpu_uuid(1)}, 31337, python, 2048 MiB",
    )
    assert run.run() == 0, run.stderr_text()
    assert run.env_file("gpu-prolog.env") == {
        "foreign_compute_processes": "0",
        "allow_shared_gpu": "false",
        "decision": "exclusive",
    }


@RUNTIME_SKIP
def test_allow_shared_gpu_admits_a_busy_gpu_and_records_it(lane_root: Path) -> None:
    raw = _seeded_raw()
    raw["allow_shared_gpu"] = True
    raw["shared_gpu_reason"] = SHARED_GPU_REASON
    run = StubbedRun(
        lane_root, raw, FAKE_COMPUTE_APPS=f"{_gpu_uuid(0)}, 31337, python, 2048 MiB"
    )
    assert run.run() == 0, run.stderr_text()
    assert run.env_file("gpu-prolog.env") == {
        "foreign_compute_processes": "1",
        "allow_shared_gpu": "true",
        "decision": "shared_allowed",
    }
    assert run.env_file("job.env")["allow_shared_gpu"] == "true"


@RUNTIME_SKIP
def test_unreadable_gpu_process_list_fails_closed(lane_root: Path) -> None:
    run = StubbedRun(lane_root, _seeded_raw(), FAKE_COMPUTE_APPS_STATUS="9")
    assert run.run() == 2, run.stderr_text()
    assert run.calls("create") == []
    assert run.env_file("termination.env")["reason"] == "gpu_prolog_unavailable"


SIGNAL_MARKER = "trigger=SIGUSR1\nstep=signal-checkpoint"


@RUNTIME_SKIP
@pytest.mark.parametrize(
    ("periodic_marker", "mode", "inspect_save", "confirmed", "marker"),
    [
        # The original regression: a stale periodic marker confirmed the signal.
        ("true", "stop-on-signal", "false", False, "step=periodic-checkpoint"),
        ("false", "stop-on-signal", "false", False, None),
        # A stale marker never confirms, even one that names the trigger.
        ("stale-trigger", "stop-on-signal", "false", False, "trigger=SIGUSR1\nstep=stale"),
        # Review case A: a periodic save finishes during the running check.
        ("true", "stop-on-signal", "true", False, "step=periodic-"),
        # Review case B: a periodic save lands after the signal.
        ("true", "periodic-after-signal", "false", False, "step=periodic-1000"),
        # A marker written on the signal confirms only with the right trigger line.
        ("false", "untriggered-on-signal", "false", False, "step=signal-checkpoint"),
        ("false", "wrong-trigger-on-signal", "false", False, "trigger=SIGTERM"),
        ("true", "checkpoint-on-signal", "false", True, SIGNAL_MARKER),
        ("false", "checkpoint-on-signal", "false", True, SIGNAL_MARKER),
        ("stale-trigger", "checkpoint-on-signal", "false", True, SIGNAL_MARKER),
    ],
)
def test_usr1_is_forwarded_live_and_only_a_fresh_triggered_marker_confirms(
    lane_root: Path,
    periodic_marker: str,
    mode: str,
    inspect_save: str,
    confirmed: bool,
    marker: str | None,
) -> None:
    run = StubbedRun(
        lane_root,
        _seeded_raw(),
        FAKE_WORKLOAD_MODE=mode,
        FAKE_PERIODIC_MARKER=periodic_marker,
        FAKE_PERIODIC_SAVE_ON_INSPECT=inspect_save,
    )
    run.start()
    run.wait_for_workload()
    assert run.process is not None
    run.process.send_signal(signal.SIGUSR1)
    assert run.finish() == 0, run.stderr_text()
    assert (run.state / "workload-signals").read_text(encoding="utf-8").split() == ["USR1"]
    assert ["kill", "--signal", "USR1", "cotcodec-4242"] in run.calls("kill")
    termination = run.env_file("termination.env")
    outcome = "confirmed" if confirmed else "missing"
    assert termination["reason"] == f"signal_USR1_checkpoint_{outcome}"
    # checkpoint_ready reports the confirmation, not the bare existence of a marker.
    assert termination["checkpoint_ready"] == str(confirmed).lower()
    assert termination["checkpoint_marker_present"] == str(marker is not None).lower()
    path = run.run_dir / "checkpoint.ready"
    if marker is None:
        assert not path.exists()
    else:
        assert path.read_text(encoding="utf-8").strip().startswith(marker)


@RUNTIME_SKIP
def test_completed_job_with_a_leftover_marker_is_not_checkpoint_ready(lane_root: Path) -> None:
    run = StubbedRun(lane_root, _seeded_raw(), FAKE_PERIODIC_MARKER="stale-trigger")
    assert run.run() == 0, run.stderr_text()
    termination = run.env_file("termination.env")
    assert termination["reason"] == "completed"
    assert termination["checkpoint_ready"] == "false"
    assert termination["checkpoint_marker_present"] == "true"
