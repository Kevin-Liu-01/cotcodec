#!/usr/bin/env python3
# ruff: noqa: E501
"""Apply the CoTCodec checkpoint hooks to one exact PAST-Bench checkout.

The upstream source remains separately verifiable and unmodified in the build
context.  The candidate image runs that verification first, then this script
performs exact, one-occurrence source transformations and installs the
CoTCodec-owned checkpoint primitive.  Any upstream drift fails closed.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

UPSTREAM_CLI_SHA256 = "5fb9338988ff5672d5338f15808c6c56d422dc948c71318714b97a5f10f5f3ff"


class CheckpointOverlayError(ValueError):
    """Raised when the exact upstream checkpoint overlay cannot be applied."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_regular(path: Path, *, owner: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise CheckpointOverlayError(f"{owner} is not a readable regular file") from exc
    try:
        info = os.fstat(descriptor)
        if not (info.st_mode & 0o170000) == 0o100000:
            raise CheckpointOverlayError(f"{owner} is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, value: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary.exists():
            temporary.unlink()


TRANSFORMS = [
    (
        "import shutil\nimport sys\n",
        "import shutil\nimport signal\nimport sys\n",
    ),
    (
        "    from .runner.services import ServiceManager\n\n    cfg = load_config(args.config)\n",
        "    from .runner.cotcodec_checkpoint import (\n"
        "        CheckpointStore,\n"
        "        load_execution_identity,\n"
        "    )\n"
        "    from .runner.services import ServiceManager\n\n"
        "    cfg = load_config(args.config)\n",
    ),
    (
        '''    if args.trace_dir:\n        trace_root = Path(args.trace_dir)\n        trace_root.mkdir(parents=True, exist_ok=True)\n    else:\n        trace_root = _make_trace_dir(cfg.defaults.trace_dir, f"{args.agent}_{sequence.name}")\n\n    variants = [("with_persistence", True)]\n''',
        '''    checkpoint_store = None\n    checkpoint_state = None\n    checkpoint_stop = {"requested": False}\n    if args.trace_dir:\n        trace_root = Path(args.trace_dir).resolve()\n    else:\n        if getattr(args, "checkpoint_dir", None):\n            raise SystemExit("--trace-dir is required with --checkpoint-dir")\n        trace_root = _make_trace_dir(cfg.defaults.trace_dir, f"{args.agent}_{sequence.name}")\n\n    checkpoint_dir = getattr(args, "checkpoint_dir", None)\n    if checkpoint_dir:\n        if sequence.mode != "episodes":\n            raise SystemExit("checkpointing is supported only for episode sequences")\n        identity_path = getattr(args, "checkpoint_identity", None)\n        if not identity_path:\n            raise SystemExit("--checkpoint-identity is required with --checkpoint-dir")\n        marker_value = os.environ.get("COTCODEC_CHECKPOINT_MARKER", "")\n        checkpoint_store = CheckpointStore(\n            checkpoint_root=Path(checkpoint_dir),\n            trace_root=trace_root,\n            identity=load_execution_identity(Path(identity_path)),\n            marker=Path(marker_value) if marker_value else None,\n        )\n        if getattr(args, "resume_checkpoint", False):\n            checkpoint_state = checkpoint_store.restore_latest()["state"]\n        else:\n            if trace_root.exists() and any(trace_root.iterdir()):\n                raise SystemExit("new checkpointed trace root must be absent or empty")\n            trace_root.mkdir(parents=True, exist_ok=True)\n\n        def _request_checkpoint_stop(_signum, _frame):\n            checkpoint_stop["requested"] = True\n\n        if hasattr(signal, "SIGUSR1"):\n            signal.signal(signal.SIGUSR1, _request_checkpoint_stop)\n    else:\n        trace_root.mkdir(parents=True, exist_ok=True)\n        if getattr(args, "resume_checkpoint", False):\n            raise SystemExit("--resume-checkpoint requires --checkpoint-dir")\n        if getattr(args, "stop_after_episode", None) is not None:\n            raise SystemExit("--stop-after-episode requires --checkpoint-dir")\n\n    stop_after_episode = getattr(args, "stop_after_episode", None)\n    if stop_after_episode is not None and stop_after_episode < 1:\n        raise SystemExit("--stop-after-episode must be positive")\n\n    variants = [("with_persistence", True)]\n''',
    ),
    (
        '''    shared_cold_homes: dict[str, Path] = {}          # family_id → saved runtime state root\n    shared_cold_episode_results: dict[int, dict] = {}  # episode index → graded result\n    shared_cold_trace_paths: dict[int, Path] = {}      # episode index → .jsonl path\n\n    if persistence_backend is not None and any(ep.shared_cold_run for ep in sequence.episodes):\n''',
        '''    shared_cold_homes: dict[str, Path] = {}          # family_id → saved runtime state root\n    shared_cold_episode_results: dict[int, dict] = {}  # episode index → graded result\n    shared_cold_trace_paths: dict[int, Path] = {}      # episode index → .jsonl path\n\n    def _checkpoint_relative(path: Path) -> str:\n        return path.resolve().relative_to(trace_root).as_posix()\n\n    def _checkpoint_path(value: str) -> Path:\n        path = (trace_root / value).resolve()\n        if path != trace_root and trace_root not in path.parents:\n            raise RuntimeError("checkpoint path escapes the trace root")\n        return path\n\n    def _shared_checkpoint_state() -> dict:\n        return {\n            "homes": {\n                key: _checkpoint_relative(path) for key, path in shared_cold_homes.items()\n            },\n            "episode_results": {\n                str(key): value for key, value in shared_cold_episode_results.items()\n            },\n            "trace_paths": {\n                str(key): _checkpoint_relative(path)\n                for key, path in shared_cold_trace_paths.items()\n            },\n        }\n\n    restored_shared = {}\n    if checkpoint_state is not None:\n        extra_state = checkpoint_state.get("extra_state", {})\n        if not isinstance(extra_state, dict):\n            raise RuntimeError("checkpoint extra state is invalid")\n        restored_shared = extra_state.get("shared_cold", {})\n        if not isinstance(restored_shared, dict):\n            raise RuntimeError("checkpoint shared-cold state is invalid")\n    if restored_shared:\n        homes = restored_shared.get("homes", {})\n        results = restored_shared.get("episode_results", {})\n        traces = restored_shared.get("trace_paths", {})\n        if not all(isinstance(value, dict) for value in (homes, results, traces)):\n            raise RuntimeError("checkpoint shared-cold fields are invalid")\n        shared_cold_homes = {key: _checkpoint_path(value) for key, value in homes.items()}\n        shared_cold_episode_results = {int(key): value for key, value in results.items()}\n        shared_cold_trace_paths = {\n            int(key): _checkpoint_path(value) for key, value in traces.items()\n        }\n\n    if not restored_shared and persistence_backend is not None and any(\n        ep.shared_cold_run for ep in sequence.episodes\n    ):\n''',
    ),
    (
        '''    # ── end shared cold pre-pass ─────────────────────────────────────────────────\n\n    for variant_label, persistence_enabled in variants:\n        variant_dir = trace_root / variant_label if len(variants) > 1 else trace_root\n        variant_dir.mkdir(parents=True, exist_ok=True)\n        family_homes_root = variant_dir / "family_homes"\n        history_anchors_by_family: dict[str, dict[str, Path]] = {}\n        if persistence_backend is not None:\n            _reset_runtime_dir(family_homes_root)\n        episode_results: list[dict] = []\n\n        print(f"\\n=== Sequence: {sequence.name} [{variant_label}] ===")\n''',
        '''    # ── end shared cold pre-pass ─────────────────────────────────────────────────\n+\n+    if checkpoint_store is not None and not restored_shared and shared_cold_episode_results:\n+        checkpoint_store.commit(\n+            stage="shared-cold-complete",\n+            variant=None,\n+            completed_episode=0,\n+            episode_results=[],\n+            extra_state={"shared_cold": _shared_checkpoint_state()},\n+        )\n+\n+    variant_labels = [label for label, _enabled in variants]\n+    resume_variant = checkpoint_state.get("variant") if checkpoint_state else None\n+    resume_variant_index = (\n+        variant_labels.index(resume_variant) if resume_variant in variant_labels else None\n+    )\n+    for variant_index, (variant_label, persistence_enabled) in enumerate(variants):\n+        variant_dir = trace_root / variant_label if len(variants) > 1 else trace_root\n+        variant_dir.mkdir(parents=True, exist_ok=True)\n+        if checkpoint_state and checkpoint_state.get("stage") == "run-complete":\n+            variant_summaries[variant_label] = json.loads(\n+                (variant_dir / "sequence_summary.json").read_text(encoding="utf-8")\n+            )\n+            continue\n+        if resume_variant_index is not None and variant_index < resume_variant_index:\n+            variant_summaries[variant_label] = json.loads(\n+                (variant_dir / "sequence_summary.json").read_text(encoding="utf-8")\n+            )\n+            continue\n+        if (\n+            resume_variant_index == variant_index\n+            and checkpoint_state\n+            and checkpoint_state.get("stage") == "variant-complete"\n+        ):\n+            variant_summaries[variant_label] = json.loads(\n+                (variant_dir / "sequence_summary.json").read_text(encoding="utf-8")\n+            )\n+            continue\n+\n+        family_homes_root = variant_dir / "family_homes"\n+        history_anchors_by_family: dict[str, dict[str, Path]] = {}\n+        completed_episode = 0\n+        episode_results: list[dict] = []\n+        if (\n+            resume_variant_index == variant_index\n+            and checkpoint_state\n+            and checkpoint_state.get("stage") == "episode-complete"\n+        ):\n+            completed_episode = int(checkpoint_state.get("completed_episode", 0))\n+            episode_results = list(checkpoint_state.get("episode_results", []))\n+            if persistence_backend is not None:\n+                for registered_episode in sequence.episodes:\n+                    _, registered_anchors = persistence_backend.family_paths(\n+                        variant_dir, registered_episode.family_id\n+                    )\n+                    family_anchors = history_anchors_by_family.setdefault(\n+                        registered_episode.family_id, {}\n+                    )\n+                    if registered_anchors.is_dir():\n+                        for anchor_path in registered_anchors.iterdir():\n+                            if anchor_path.is_dir() and not anchor_path.is_symlink():\n+                                family_anchors[anchor_path.name] = anchor_path\n+        elif persistence_backend is not None:\n+            _reset_runtime_dir(family_homes_root)\n+\n+        print(f"\\n=== Sequence: {sequence.name} [{variant_label}] ===")\n''',
    ),
    (
        '''        checkpoint_store.commit(\n            stage="shared-cold-complete",\n            variant=None,\n            completed_episode=0,\n            episode_results=[],\n            extra_state={"shared_cold": _shared_checkpoint_state()},\n        )\n\n    variant_labels = [label for label, _enabled in variants]\n''',
        '''        checkpoint_store.commit(\n            stage="shared-cold-complete",\n            variant=None,\n            completed_episode=0,\n            episode_results=[],\n            extra_state={"shared_cold": _shared_checkpoint_state()},\n        )\n+        if checkpoint_stop["requested"]:\n+            print("CHECKPOINT_STOP stage=shared-cold-complete")\n+            return\n+\n+    variant_labels = [label for label, _enabled in variants]\n''',
    ),
    (
        '''            artifacts_dir = episode_dir / "artifacts"\n            if persistence_backend is not None:\n''',
        '''            artifacts_dir = episode_dir / "artifacts"\n            if index <= completed_episode:\n                print(\n                    f"\\n[{index}/{len(sequence.episodes)}] [checkpoint reuse] "\n                    f"family={episode.family_id} task={task.task_id}"\n                )\n                continue\n            if persistence_backend is not None:\n''',
    ),
    (
        '''                print(\n                    f"\\n[{index}/{len(sequence.episodes)}] [shared cold → {variant_label}] "\n                    f"family={episode.family_id} task={task.task_id} "\n                    f"score={shared_cold_episode_results[index]['task_score']:.3f} "\n                    f"passed={shared_cold_episode_results[index]['passed']}"\n                )\n                continue\n''',
        '''                print(\n                    f"\\n[{index}/{len(sequence.episodes)}] [shared cold → {variant_label}] "\n                    f"family={episode.family_id} task={task.task_id} "\n                    f"score={shared_cold_episode_results[index]['task_score']:.3f} "\n                    f"passed={shared_cold_episode_results[index]['passed']}"\n                )\n+                if checkpoint_store is not None:\n+                    checkpoint_store.commit(\n+                        stage="episode-complete",\n+                        variant=variant_label,\n+                        completed_episode=index,\n+                        episode_results=episode_results,\n+                        extra_state={"shared_cold": _shared_checkpoint_state()},\n+                    )\n+                    if checkpoint_stop["requested"] or stop_after_episode == index:\n+                        print(\n+                            f"CHECKPOINT_STOP variant={variant_label} "\n+                            f"completed_episode={index}"\n+                        )\n+                        return\n+                continue\n''',
    ),
    (
        '''                print(\n                    "  reflection "\n                    f"memory={reflection_result['artifacts']['memory_chars']} "\n                    f"skills={reflection_result['artifacts']['skill_count']} "\n                    f"internal(memory={reflection_result['internal_tools'].get('memory_calls', 0)}, "\n                    f"skill={reflection_result['internal_tools'].get('skill_manage_calls', 0)}, "\n                    f"search={reflection_result['internal_tools'].get('session_search_calls', 0)})"\n                )\n\n        summary = summarize_sequence(\n''',
        '''                print(\n                    "  reflection "\n                    f"memory={reflection_result['artifacts']['memory_chars']} "\n                    f"skills={reflection_result['artifacts']['skill_count']} "\n                    f"internal(memory={reflection_result['internal_tools'].get('memory_calls', 0)}, "\n                    f"skill={reflection_result['internal_tools'].get('skill_manage_calls', 0)}, "\n                    f"search={reflection_result['internal_tools'].get('session_search_calls', 0)})"\n                )\n+\n+            if checkpoint_store is not None:\n+                checkpoint_store.commit(\n+                    stage="episode-complete",\n+                    variant=variant_label,\n+                    completed_episode=index,\n+                    episode_results=episode_results,\n+                    extra_state={"shared_cold": _shared_checkpoint_state()},\n+                )\n+                if checkpoint_stop["requested"] or stop_after_episode == index:\n+                    print(\n+                        f"CHECKPOINT_STOP variant={variant_label} completed_episode={index}"\n+                    )\n+                    return\n+\n+        summary = summarize_sequence(\n''',
    ),
    (
        '''        variant_summaries[variant_label] = summary\n\n        print(f"\\nSummary [{variant_label}]")\n''',
        '''        variant_summaries[variant_label] = summary\n+        if checkpoint_store is not None:\n+            checkpoint_store.commit(\n+                stage="variant-complete",\n+                variant=variant_label,\n+                completed_episode=len(sequence.episodes),\n+                episode_results=episode_results,\n+                extra_state={"shared_cold": _shared_checkpoint_state()},\n+            )\n+\n+        print(f"\\nSummary [{variant_label}]")\n''',
    ),
    (
        '''        print(\n            "  family improvement delta: "\n            f"score={comparison['delta']['avg_family_task_score_delta']:.3f} "\n            f"pass_rate={comparison['delta']['avg_family_pass_rate_delta']:.3f}"\n        )\n\n\ndef cmd_list(args: argparse.Namespace) -> None:\n''',
        '''        print(\n            "  family improvement delta: "\n            f"score={comparison['delta']['avg_family_task_score_delta']:.3f} "\n            f"pass_rate={comparison['delta']['avg_family_pass_rate_delta']:.3f}"\n        )\n+\n+    if checkpoint_store is not None:\n+        checkpoint_store.commit(\n+            stage="run-complete",\n+            variant=None,\n+            completed_episode=len(sequence.episodes),\n+            episode_results=[],\n+            extra_state={"shared_cold": _shared_checkpoint_state()},\n+        )\n+\n+\n+def cmd_list(args: argparse.Namespace) -> None:\n''',
    ),
    (
        '''    p_evolve.add_argument("--background-review-wait-s", type=float, default=None, help="Wait time after Hermes finishes so background memory/skill review can flush")\n\n    # cleanup\n''',
        '''    p_evolve.add_argument("--background-review-wait-s", type=float, default=None, help="Wait time after Hermes finishes so background memory/skill review can flush")\n+    p_evolve.add_argument("--checkpoint-dir", default=None, help="Persistent directory for immutable episode-boundary checkpoint generations")\n+    p_evolve.add_argument("--checkpoint-identity", default=None, help="Exact JSON execution identity bound into every checkpoint")\n+    p_evolve.add_argument("--resume-checkpoint", action="store_true", help="Validate and resume the latest immutable checkpoint")\n+    p_evolve.add_argument("--stop-after-episode", type=int, default=None, help="Checkpoint and exit cleanly after this episode index (recovery doctor only)")\n+\n+    # cleanup\n''',
    ),
]


def apply_overlay(*, source_root: Path, checkpoint_module: Path) -> dict[str, str]:
    source_root = source_root.resolve()
    cli_path = source_root / "src/past_bench/cli.py"
    target_module = source_root / "src/past_bench/runner/cotcodec_checkpoint.py"
    cli_bytes = _read_regular(cli_path, owner="PAST-Bench CLI")
    if _sha256(cli_bytes) != UPSTREAM_CLI_SHA256:
        raise CheckpointOverlayError("PAST-Bench CLI differs from the registered upstream hash")
    checkpoint_bytes = _read_regular(checkpoint_module, owner="checkpoint runtime module")
    text = cli_bytes.decode("utf-8")
    for old, new in TRANSFORMS:
        # Multi-line replacement literals are kept visually diff-shaped above;
        # strip their non-source leading markers before applying them.
        new = new.replace("\n+", "\n")
        if text.count(old) != 1:
            raise CheckpointOverlayError("PAST-Bench checkpoint transform sentinel drifted")
        text = text.replace(old, new, 1)
    _atomic_write(cli_path, text.encode("utf-8"))
    target_module.parent.mkdir(parents=True, exist_ok=True)
    if target_module.exists():
        raise CheckpointOverlayError("checkpoint runtime target already exists")
    temporary = target_module.with_name(f".{target_module.name}.staging")
    _atomic_write(temporary, checkpoint_bytes)
    os.rename(temporary, target_module)
    return {
        "upstream_cli_sha256": UPSTREAM_CLI_SHA256,
        "patched_cli_sha256": _sha256(text.encode("utf-8")),
        "checkpoint_module_sha256": _sha256(checkpoint_bytes),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--checkpoint-module", type=Path, required=True)
    args = parser.parse_args()
    receipt = apply_overlay(
        source_root=args.source_root,
        checkpoint_module=args.checkpoint_module,
    )
    print(" ".join(f"{key}={value}" for key, value in sorted(receipt.items())))


if __name__ == "__main__":
    main()
