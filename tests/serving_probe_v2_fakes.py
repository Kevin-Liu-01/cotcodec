"""Fakes for the serving-throughput-probe-v2 tests (not collected: no ``test_`` prefix).

* :class:`FakeVllmIds` is v1's fake server that also streams ``prompt_token_ids``
  in the first chunk when a request sets ``return_token_ids`` (vLLM v0.31.0).
* :class:`FakeSampler` reports a settable device memory for any window.
* :class:`FakeApps` replays a timeline of compute-process listings.
* :class:`FakeEngine` is a server engine whose start and stop move both.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

import httpx
import numpy as np
from serving_probe_fakes import IMAGE_TOKENS, WRAPPER_TOKENS, FakeVllm, WordTokenizer

from harness.serving_probe.metrics import GpuSample, parse_prometheus
from harness.serving_probe_v2.contamination import UNRESOLVED, AppRow, AppsSnapshot

GPU_UUID = "GPU-00000000-1111-2222-3333-444444444444"
ENGINE_HOST_PID = 1824294
#: Device memory no process accounts for (driver bookkeeping) in the fakes.
DEVICE_GAP_MIB = 300.0


def prompt_ids(messages: list[dict[str, Any]]) -> list[int]:
    """Deterministic prompt ids: text words, then each image's placeholder run."""
    tokenizer = WordTokenizer()
    ids: list[int] = []
    for message in messages:
        for part in message["content"]:
            if part["type"] == "text":
                ids.extend(tokenizer.encode(part["text"]))
                ids.append(1)
            else:
                url = part["image_url"]["url"]
                token = 3 + int(hashlib.sha256(url.encode()).hexdigest()[:6], 16) % 400
                ids.extend([token] * (IMAGE_TOKENS + WRAPPER_TOKENS))
    return ids


class FakeVllmIds(FakeVllm):
    """v1's fake server plus ``prompt_token_ids`` in the first streamed chunk."""

    def __init__(self, *, return_prompt_ids: bool = True, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.return_prompt_ids = return_prompt_ids

    def _stream(self, body: dict[str, Any], prompt: int, output: int) -> bytes:
        stream = super()._stream(body, prompt, output)
        if not (body.get("return_token_ids") and self.return_prompt_ids):
            return stream
        first = {
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}}],
            "prompt_token_ids": prompt_ids(body["messages"])[:prompt],
        }
        return f"data: {json.dumps(first)}\n\n".encode() + stream


class FakeSampler:
    """Device samples at 10 ms spacing over any window, at the current memory."""

    def __init__(self) -> None:
        self.memory = 0.0
        self.util = 0.0
        self.dead = False
        #: (time, memory) changes, so a window sees the memory of its own time.
        self.timeline: list[tuple[float, float]] = [(0.0, 0.0)]

    def set_memory(self, memory: float) -> None:
        self.memory = memory
        self.timeline.append((time.perf_counter(), memory))

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def _at(self, t: float) -> float:
        value = 0.0
        for when, memory in self.timeline:
            if when <= t:
                value = memory
        return value

    def window(self, start: float, end: float) -> list[GpuSample]:
        if self.dead:
            return []
        times = np.arange(start, max(end, start + 0.01), 0.01)
        return [GpuSample(float(t), self._at(float(t)), self.util, 100.0, 1980.0) for t in times]


class FakeApps:
    """Compute-process listings over time; ``mode`` sets how the engine appears.

    ``host``: the engine as one unresolved host-namespace PID (NVML in a container);
    ``empty``: NVML lists nothing; ``broken``: every query fails.
    """

    def __init__(self, sampler: FakeSampler, mode: str = "host") -> None:
        self.sampler = sampler
        self.mode = mode
        self.engine_rows: tuple[AppRow, ...] = ()
        self.extra: tuple[AppRow, ...] = ()
        self.timeline: list[tuple[float, tuple[AppRow, ...]]] = [(0.0, ())]

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def _push(self) -> None:
        self.timeline.append((time.perf_counter(), self.engine_rows + self.extra))

    def engine_started(self, memory: float) -> None:
        if self.mode == "host":
            used = memory - DEVICE_GAP_MIB
            self.engine_rows = (AppRow(GPU_UUID, ENGINE_HOST_PID, "[Not Found]", used, UNRESOLVED),)
        self._push()

    def engine_stopped(self) -> None:
        self.engine_rows = ()
        self._push()

    def set_extra(self, rows: tuple[AppRow, ...]) -> None:
        """Rows listed from now on next to the engine's (a foreign process)."""
        self.extra = rows
        self._push()

    def _rows_at(self, t: float) -> tuple[AppRow, ...]:
        rows: tuple[AppRow, ...] = ()
        for when, listed in self.timeline:
            if when <= t:
                rows = listed
        return rows

    def window(self, start: float, end: float) -> list[AppsSnapshot]:
        times = np.arange(start, max(end, start + 0.01), 0.01)
        snapshots = []
        for t in times:
            t = float(t)
            if self.mode == "broken":
                snapshots.append(AppsSnapshot(t, False, error="nvidia-smi failed"))
                continue
            device = self.sampler._at(t)
            snapshots.append(AppsSnapshot(t, True, self._rows_at(t), device))
        return snapshots


class FakeEngine:
    mode = "server"
    served_name = "probe-model"

    def __init__(
        self,
        server: FakeVllmIds,
        model_dir: str,
        sampler: FakeSampler,
        apps: FakeApps,
        *,
        memory: float = 74301.0,
        ready: bool = True,
    ) -> None:
        self.server = server
        self.model_dir = model_dir
        self.sampler = sampler
        self.apps = apps
        self.memory = memory
        self.ready = ready
        self.pid = os.getpid()
        self.eager: bool | None = None

    def argv(self, eager: bool) -> list[str]:
        return ["vllm", "serve", self.model_dir] + (["--enforce-eager"] if eager else [])

    def start(self, eager: bool) -> None:
        self.eager = eager
        self.sampler.set_memory(self.memory)
        self.apps.engine_started(self.memory)

    def wait_ready(self, timeout_s: float, should_stop=None) -> bool:
        return self.ready

    def alive(self) -> bool:
        return self.server.alive

    def metrics(self) -> dict[str, float]:
        with self.server.sync_client() as client:
            return parse_prometheus(client.get("/metrics").text)

    def reset_caches(self) -> dict[str, Any]:
        with self.server.sync_client() as client:
            ok = client.post("/reset_prefix_cache").json()["success"]
        return {"prefix": ok, "mm": True, "encoder": True}

    def async_client(self) -> httpx.AsyncClient:
        return self.server.async_client()

    def log_text(self) -> str:
        return "INFO GPU KV cache size: 1,000 tokens\n"

    def tmp_maps(self) -> dict[str, list[str]]:
        return {}

    def stop(self, timeout_s: float = 30.0) -> dict[str, Any]:
        self.sampler.set_memory(0.0)
        self.apps.engine_stopped()
        return {"returncode": 0}
