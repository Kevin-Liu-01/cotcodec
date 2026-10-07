#!/usr/bin/env python3
"""Repair known defects of the pinned vLLM base image and prove its serving path imports.

Run once at overlay build time (no network). Found on 2026-10-07 in
``vllm/vllm-openai:v0.31.0-cu129`` (amd64 manifest sha256:b18abb2d...): the image
ships torchcodec 0.17.0 built against CUDA 13 (``libcudart.so.13``,
``libnvrtc.so.13``), which a CUDA 12.9 image does not contain. ``import
torchcodec`` then raises OSError, which vLLM's guard in
``vllm/multimodal/media/audio.py`` (ImportError, RuntimeError) does not catch, so
``vllm serve`` dies while importing ``vllm.engine.arg_utils``. torchcodec only
decodes audio and video; the probe sends images and sets the video limit to 0.
Removing it turns the failure into the ImportError vLLM already handles.

Every action is written to a JSON record that the overlay builder copies into its
build receipt. A package is removed only when importing it raises OSError.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from collections.abc import Callable, Sequence
from importlib import metadata
from pathlib import Path
from typing import Any

#: Packages that may be removed, and only when their import fails with OSError.
REMOVABLE_ON_OSERROR = ("torchcodec",)
#: Modules ``vllm serve`` and the probe must be able to import after the fixups.
REQUIRED_IMPORTS = (
    "vllm.engine.arg_utils",
    "vllm.entrypoints.launchers.cli_args",
    "vllm.multimodal",
    "transformers",
)


def probe_import(module: str, importer: Callable[[str], Any]) -> str | None:
    """Return the OSError text if importing ``module`` hits a broken shared library."""
    try:
        importer(module)
    except OSError as exc:
        return f"{type(exc).__name__}: {exc}"[:500]
    except ImportError:
        return None
    return None


def run_fixups(
    *,
    importer: Callable[[str], Any] = importlib.import_module,
    runner: Callable[..., Any] = subprocess.run,
    version_of: Callable[[str], str] = metadata.version,
) -> dict[str, Any]:
    actions: list[dict[str, str]] = []
    for package in REMOVABLE_ON_OSERROR:
        error = probe_import(package, importer)
        if error is None:
            continue
        version = version_of(package)
        runner(
            [
                sys.executable,
                "-m",
                "pip",
                "uninstall",
                "-y",
                "--root-user-action",
                "ignore",
                package,
            ],
            check=True,
        )
        actions.append(
            {"package": package, "version": version, "action": "uninstalled", "reason": error}
        )
        for name in [m for m in sys.modules if m == package or m.startswith(package + ".")]:
            del sys.modules[name]
        importlib.invalidate_caches()
    for module in REQUIRED_IMPORTS:
        importer(module)
    return {"schema_version": 1, "actions": actions, "required_imports": list(REQUIRED_IMPORTS)}


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        raise SystemExit("usage: vllm_overlay_fixups.py OUTPUT_JSON")
    record = run_fixups()
    Path(args[0]).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"actions": len(record["actions"]), "status": "PASS"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
