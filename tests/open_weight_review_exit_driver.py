"""Exit-path driver for the open-weight reviewer (not collected: no ``test_`` prefix).

Runs ``scripts/run_open_weight_review.py``'s real entry point in its own process
with an engine that reproduces what hung smoke job 617: a non-daemon thread that
never ends and a ``close`` that never returns. Used by
``tests/test_open_weight_review.py`` and, as PID 1, inside the overlay image:

    python tests/open_weight_review_exit_driver.py hang-exit <workdir>
    python tests/open_weight_review_exit_driver.py block <workdir>

``hang-exit`` must still exit 0 promptly with a parsed review. ``block`` writes
``<workdir>/generating`` and then generates until a signal arrives; USR1 or TERM
must end it with exit 3, a receipt and (with ``COTCODEC_CHECKPOINT_MARKER``) the
lane marker.
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import run_open_weight_review as owr  # noqa: E402

REVIEWER = PROJECT_ROOT / "experiments" / "reviewer"
ANSWER = {"falsifiability_score": 7, "has_falsifier": True, "largest_defect": "Trivial."}


class DriverEngine:
    def __init__(self, mode: str, workdir: Path) -> None:
        self.mode = mode
        self.workdir = workdir
        # Interpreter shutdown joins non-daemon threads: this one never ends.
        threading.Thread(target=threading.Event().wait, name="never-ends", daemon=False).start()

    def render(self, message: str, *, thinking: bool) -> owr.RenderedPrompt:
        return owr.RenderedPrompt(text=message, token_ids=tuple(range(16)))

    def generate(
        self, prompt: owr.RenderedPrompt, *, seeds: Sequence[int], max_tokens: int
    ) -> list[owr.Completion]:
        if self.mode == "block":
            (self.workdir / "generating").write_text("1\n", encoding="utf-8")
            while True:  # the signal handler raises out of this loop
                time.sleep(0.05)
        text = json.dumps(ANSWER)
        return [owr.Completion(text=text, token_ids=(1, 2, 3), finish_reason="stop") for _ in seeds]

    def facts(self) -> dict[str, Any]:
        return {"vllm_version": "exit-driver"}

    def close(self) -> None:
        threading.Event().wait()  # never returns: close_engine must give up


def prepare(workdir: Path) -> list[str]:
    model_dir = workdir / "models" / "qwen3.5-9b"
    model_dir.mkdir(parents=True)
    config = b'{"model_type": "qwen3_5"}'
    (model_dir / "config.json").write_bytes(config)
    receipt = {
        "model_id": "qwen3.5-9b",
        "backend": "huggingface",
        "mode": "full",
        "revision": "0" * 40,
        "artifact_root_sha256": "0" * 64,
        "files": [
            {
                "path": "config.json",
                "bytes": len(config),
                "sha256": hashlib.sha256(config).hexdigest(),
            }
        ],
    }
    receipt_path = workdir / "qwen3.5-9b.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return [
        "run",
        "--prompt-file",
        str(REVIEWER / "smoke-prompt.txt"),
        "--schema-file",
        str(REVIEWER / "smoke-schema.json"),
        "--model-dir",
        str(model_dir),
        "--model-receipt",
        str(receipt_path),
        "--expected-model-receipt-sha256",
        hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "--output-dir",
        str(workdir / "review"),
        "--thinking",
        "off",
        "--seeds",
        "42",
        "43",
        "44",
    ]


def main() -> None:
    mode, workdir = sys.argv[1], Path(sys.argv[2])
    if mode not in {"hang-exit", "block"}:
        raise SystemExit("mode must be hang-exit or block")
    workdir.mkdir(parents=True, exist_ok=True)
    owr.ENGINE_CLOSE_TIMEOUT_S = 1.0
    argv = prepare(workdir)
    owr.entrypoint(argv, engine_factory=lambda settings, model_dir: DriverEngine(mode, workdir))


if __name__ == "__main__":
    main()
