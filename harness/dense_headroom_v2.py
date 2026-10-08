"""What q3-dense-headroom-precheck-v2 adds to v1's inputs and statistics (torch-free).

Program decision D36 ran ``q3-dense-headroom-precheck-v2`` with v1's data,
statistics, decision rules and thresholds unchanged: v2 imports
``harness/dense_headroom_data.py`` and ``harness/dense_headroom_stats.py``
byte for byte. This module holds only what v1 lacked:

* ``SignalGuard``: SIGUSR1 and SIGTERM reach the evaluation loop whatever a
  native library does to the process's signal dispositions. v1's 4B job (Slurm
  730) ignored Slurm's SIGUSR1 because LLVM, linked into Triton, installs its
  own process-wide handlers the first time a kernel is compiled (the
  flash-linear-attention kernels compile inside the first forward). LLVM's
  handler for SIGUSR1 (an "info" signal) swallows it, so CPython's handler,
  installed earlier, never ran. The guard blocks both signals in every thread
  from process start (a blocked signal stays pending whatever the handler, and
  a blocked signal is never discarded, even for a container's PID 1), polls
  and consumes them at safe points with ``sigpending``/``sigwait``, keeps
  CPython's handler installed as a second path, and re-installs it whenever
  the OS-level handler has been replaced (each replacement is recorded).
* ``batch_job_id``: the Slurm job a receipt belongs to. Inside the container
  ``SLURM_JOB_ID`` is unset (the batch script does not pass it), so v1's
  receipts carried ``slurm_job_id: null`` and the summariser refused them.
  The batch script writes ``job.env`` (first line ``job_id=<N>``) into the
  job's run directory, which is the container's ``/outputs``, before the
  container is created; the entry point reads the id from there.
* ``v1_reproduction``: the registered validity gate that v2's
  Qwen3-0.6B-Base lane reproduces v1's job-727 receipt statistics (every
  numeric leaf to 1e-6, every other leaf exactly).
* The timing job's registered order of development units.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import json
import math
import re
import signal
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

EXPERIMENT_ID = "q3-dense-headroom-precheck-v2"
V1_EXPERIMENT_ID = "q3-dense-headroom-precheck-v1"

# --------------------------------------------------------------------------- #
# The validity gate against v1's completed Qwen3-0.6B-Base receipt (Slurm 727)
# --------------------------------------------------------------------------- #

V1_SMALL_LANE_JOB = "727"
V1_SMALL_LANE_RECEIPT = ("program/evidence/2026-10-08/q3-dense-headroom-precheck/"
                         "lane-0p6b-727/receipt.json")
V1_SMALL_LANE_RECEIPT_SHA256 = "bfe4a7c33cca3cf106370876f2843239c7c88a4f3c4fb70798f8a8d6404508ba"
V1_SMALL_LANE_ARTIFACT_SHA256 = "c1c455d81425cc9ea25345ecf2bbea3e0b604853da51ea046fe315fe4b3f9e71"
V1_LARGE_LANE_ARTIFACT_SHA256 = "b5210f7935e87cc95cfb9fc56baa39d8e8162b81f8a501e49aac0c989fbfe82f"
V1_REPRODUCTION_TOLERANCE = 1e-6
# Receipt fields compared leaf by leaf: every numeric leaf within the
# tolerance (absolute, in the field's own unit), every other leaf equal, the
# same keys and list lengths everywhere. Timings, versions, code digests and
# job fields are not statistics and are not compared.
V1_REPRODUCED_FIELDS = ("report", "decisions", "coverage", "artifact_counts", "selectors",
                        "attention_layers")
V1_REPRODUCED_EXACT = (("hashes", "dev_artifact_sha256"),)


def _leaves(value: Any, path: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        yield f"{path}{{}}", tuple(sorted(str(k) for k in value))
        for key in sorted(value, key=str):
            yield from _leaves(value[key], f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        yield f"{path}[]", len(value)
        for index, item in enumerate(value):
            yield from _leaves(item, f"{path}[{index}]")
    else:
        yield path, value


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def v1_reproduction(receipt: Mapping[str, Any], v1_receipt: Mapping[str, Any],
                    tolerance: float = V1_REPRODUCTION_TOLERANCE) -> dict[str, Any]:
    """REPRODUCED when every registered field of ``receipt`` equals v1's (numeric
    leaves within ``tolerance``); FAILED otherwise, with the differing leaves."""

    mismatches: list[dict[str, Any]] = []
    numeric = 0
    exact = 0
    max_gap = 0.0
    for field in V1_REPRODUCED_FIELDS:
        ours = dict(_leaves(receipt.get(field), field))
        theirs = dict(_leaves(v1_receipt.get(field), field))
        for path in sorted(set(ours) | set(theirs)):
            if path not in ours or path not in theirs:
                mismatches.append({"leaf": path, "v1": theirs.get(path), "v2": ours.get(path)})
                continue
            a, b = ours[path], theirs[path]
            if _is_number(a) and _is_number(b):
                numeric += 1
                fa, fb = float(a), float(b)
                if math.isnan(fa) or math.isnan(fb):
                    gap = 0.0 if (math.isnan(fa) and math.isnan(fb)) else math.inf
                else:
                    gap = abs(fa - fb)
                max_gap = max(max_gap, gap)
                if gap > tolerance:
                    mismatches.append({"leaf": path, "v1": b, "v2": a, "gap": gap})
            else:
                exact += 1
                if a != b:
                    mismatches.append({"leaf": path, "v1": b, "v2": a})
    for keys in V1_REPRODUCED_EXACT:
        ours_value: Any = receipt
        theirs_value: Any = v1_receipt
        for key in keys:
            ours_value = (ours_value or {}).get(key)
            theirs_value = (theirs_value or {}).get(key)
        exact += 1
        if ours_value != theirs_value or ours_value is None:
            mismatches.append({"leaf": ".".join(keys), "v1": theirs_value, "v2": ours_value})
    return {"status": "REPRODUCED" if not mismatches else "FAILED",
            "tolerance": tolerance, "numeric_leaves": numeric, "other_leaves": exact,
            "max_numeric_gap": max_gap if numeric else None,
            "mismatches": mismatches[:20], "mismatch_count": len(mismatches),
            "v1_job": V1_SMALL_LANE_JOB, "v1_receipt_sha256": V1_SMALL_LANE_RECEIPT_SHA256,
            "fields": list(V1_REPRODUCED_FIELDS)
            + [".".join(keys) for keys in V1_REPRODUCED_EXACT]}


def load_v1_small_lane_receipt(repo_root: Path) -> dict[str, Any]:
    """The committed v1 job-727 receipt, refused unless its bytes are the recorded ones."""

    path = repo_root / V1_SMALL_LANE_RECEIPT
    raw = path.read_bytes()
    import hashlib

    if hashlib.sha256(raw).hexdigest() != V1_SMALL_LANE_RECEIPT_SHA256:
        raise ValueError(f"{path} is not v1's job-727 receipt {V1_SMALL_LANE_RECEIPT_SHA256}")
    return json.loads(raw)


# --------------------------------------------------------------------------- #
# Signals
# --------------------------------------------------------------------------- #

GUARDED_SIGNALS = (signal.SIGUSR1, signal.SIGTERM)


def block_guarded_signals() -> bool:
    """Block SIGUSR1 and SIGTERM in the calling thread (every thread started
    afterwards inherits the mask). Call it first thing in the process, before
    any library starts a thread. Returns whether blocking is available."""

    if not hasattr(signal, "pthread_sigmask"):
        return False
    signal.pthread_sigmask(signal.SIG_BLOCK, set(GUARDED_SIGNALS))
    return True


def _libc() -> Any:
    name = ctypes.util.find_library("c")
    try:
        return ctypes.CDLL(name, use_errno=True) if name else ctypes.CDLL(None, use_errno=True)
    except OSError:
        return None


_LIBC = _libc()


def os_handler_address(signum: int) -> int | None:
    """The handler address the kernel holds for ``signum`` (glibc and Darwin
    ``struct sigaction`` both start with the handler), or None if unreadable."""

    if _LIBC is None or not hasattr(_LIBC, "sigaction"):
        return None
    buffer = ctypes.create_string_buffer(512)
    if _LIBC.sigaction(int(signum), None, buffer) != 0:
        return None
    return int(ctypes.c_void_p.from_buffer(buffer).value or 0)


class SignalGuard:
    """SIGUSR1/SIGTERM for an entry point that must notice them between chunks.

    ``block_guarded_signals`` runs at process start. ``install`` sets CPython's
    handler for both signals and records the OS-level handler address that
    goes with it. ``poll`` (at every unit and chunk boundary) re-installs the
    handler if a library replaced it, consumes a pending blocked signal, and
    returns the first signal received (``SIGUSR1`` or ``SIGTERM``) or None.
    """

    def __init__(self) -> None:
        self.received: str | None = None
        self.received_at: float | None = None
        self.via: str | None = None
        self.blocked = False
        self.reference: dict[int, int | None] = {}
        self.replacements: list[dict[str, Any]] = []
        self.polls = 0
        self.started = time.monotonic()

    def _handle(self, signum: int, _frame: Any) -> None:
        self._record(signal.Signals(signum).name, "handler")

    def _record(self, name: str, via: str) -> None:
        if self.received is None:
            self.received = name
            self.received_at = time.monotonic() - self.started
            self.via = via

    def install(self) -> None:
        for signum in GUARDED_SIGNALS:
            signal.signal(signum, self._handle)
            self.reference[int(signum)] = os_handler_address(signum)
        if hasattr(signal, "pthread_sigmask"):
            current = signal.pthread_sigmask(signal.SIG_BLOCK, set())
            self.blocked = all(signum in current for signum in GUARDED_SIGNALS)

    def poll(self, where: str = "") -> str | None:
        self.polls += 1
        for signum in GUARDED_SIGNALS:
            found = os_handler_address(signum)
            reference = self.reference.get(int(signum))
            if found is None or reference is None or found != reference:
                if found is not None and reference is not None:
                    self.replacements.append({"signal": signal.Signals(signum).name,
                                              "where": where, "found": hex(found),
                                              "t": round(time.monotonic() - self.started, 3)})
                signal.signal(signum, self._handle)
                self.reference[int(signum)] = os_handler_address(signum)
        if hasattr(signal, "sigpending"):
            while True:
                pending = signal.sigpending() & set(GUARDED_SIGNALS)
                if not pending:
                    break
                got = signal.sigwait(pending)
                self._record(signal.Signals(got).name, "pending")
        return self.received

    def as_dict(self) -> dict[str, Any]:
        return {"received": self.received, "received_after_s": self.received_at,
                "via": self.via, "blocked_in_every_thread_from_start": self.blocked,
                "handler_replacements": self.replacements[:50],
                "handler_replacement_count": len(self.replacements), "polls": self.polls}


# --------------------------------------------------------------------------- #
# The receipt's Slurm job
# --------------------------------------------------------------------------- #

JOB_RE = re.compile(r"^[1-9][0-9]{0,19}$")


class JobBindingError(ValueError):
    """The job's Slurm id cannot be established (startup contract, exit code 2)."""


def read_env_file(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            fields[key] = value
    return fields


def batch_job_id(output_root: Path | None, environ: Mapping[str, str]) -> dict[str, Any]:
    """The Slurm job this process belongs to.

    Under the batch script (``output_root`` is ``COTCODEC_OUTPUT_DIR``, the
    job's run directory) the id is ``job_id`` in ``job.env``, which the batch
    script writes before the container exists; it is required there. A
    ``SLURM_JOB_ID`` in the environment must agree with it. Outside the batch
    script the id is ``SLURM_JOB_ID`` or None.
    """

    from_env = environ.get("SLURM_JOB_ID") or None
    if output_root is not None:
        path = output_root / "job.env"
        if not path.is_file():
            raise JobBindingError(f"{path} is missing: the batch script writes it before the "
                                  "container starts, so the job's Slurm id cannot be bound")
        job_id = read_env_file(path).get("job_id", "")
        if not JOB_RE.fullmatch(job_id):
            raise JobBindingError(f"{path} has no valid job_id ({job_id!r})")
        if from_env is not None and from_env != job_id:
            raise JobBindingError(f"SLURM_JOB_ID {from_env} differs from job.env's {job_id}")
        return {"slurm_job_id": job_id, "source": "job.env"}
    if from_env is not None and not JOB_RE.fullmatch(from_env):
        raise JobBindingError(f"SLURM_JOB_ID {from_env!r} is not a job id")
    return {"slurm_job_id": from_env, "source": "SLURM_JOB_ID" if from_env else "none"}


# --------------------------------------------------------------------------- #
# The timing job's order of units
# --------------------------------------------------------------------------- #

TIMING_CHUNK_UNITS = 16
TIMING_SUBSET_CHUNKS_PER_STAGE = 2


def stage_chunks(units: Sequence[Any], stages: Sequence[str],
                 chunk_units: int = TIMING_CHUNK_UNITS) -> dict[str, list[list[Any]]]:
    """Each stage's units in the lane's chunking (16 units, the lane's order)."""

    out: dict[str, list[list[Any]]] = {}
    for stage in stages:
        stage_units = [u for u in units if u.stage == stage]
        out[stage] = [stage_units[i : i + chunk_units]
                      for i in range(0, len(stage_units), chunk_units)]
    return out


def timing_order(units: Sequence[Any], stages: Sequence[str],
                 subset_chunks: int = TIMING_SUBSET_CHUNKS_PER_STAGE
                 ) -> tuple[list[tuple[str, int, list[Any]]], list[tuple[str, int, list[Any]]]]:
    """The timing job's chunks: the registered subset (the first ``subset_chunks``
    chunks of every stage, taken round robin, A1 B1 C1 D1 A2 ...), then every
    other chunk of the lane in the same round-robin order (run only to keep the
    job busy until Slurm's SIGUSR1, the live test of the signal path)."""

    chunks = stage_chunks(units, stages)
    depth = max((len(v) for v in chunks.values()), default=0)
    ordered = [(stage, index, chunks[stage][index]) for index in range(depth)
               for stage in stages if index < len(chunks[stage])]
    subset = [item for item in ordered if item[1] < subset_chunks]
    rest = [item for item in ordered if item[1] >= subset_chunks]
    return subset, rest


__all__ = [
    "EXPERIMENT_ID",
    "GUARDED_SIGNALS",
    "JOB_RE",
    "TIMING_CHUNK_UNITS",
    "TIMING_SUBSET_CHUNKS_PER_STAGE",
    "V1_EXPERIMENT_ID",
    "V1_LARGE_LANE_ARTIFACT_SHA256",
    "V1_REPRODUCED_EXACT",
    "V1_REPRODUCED_FIELDS",
    "V1_REPRODUCTION_TOLERANCE",
    "V1_SMALL_LANE_ARTIFACT_SHA256",
    "V1_SMALL_LANE_JOB",
    "V1_SMALL_LANE_RECEIPT",
    "V1_SMALL_LANE_RECEIPT_SHA256",
    "JobBindingError",
    "SignalGuard",
    "batch_job_id",
    "block_guarded_signals",
    "load_v1_small_lane_receipt",
    "os_handler_address",
    "read_env_file",
    "stage_chunks",
    "timing_order",
    "v1_reproduction",
]
