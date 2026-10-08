"""Reference store (decision D31): reference-side work once per problem, replicate and draw.

Gates (a) and (c) and audit channels A1, A2, A3 and A5 compare a candidate with
reference outputs computed on the candidate's own inputs: KernelBench's fp32
device reference, gate (c)'s validity gate (an fp64 replay and a CPU fp32
reference), and the audit's fp64 oracle with its device, TF32 and CPU fp32
references. None of these depends on the candidate. Before this pass every
item recomputed them, so a problem with ``k`` scored kernels paid for them ``k``
times per gate (and the three gate (a) variants that share KernelBench's inputs
three times more).

A **reference item** (gate ``ref_<channel>``) computes them once per problem,
replicate and channel, in its own process, with exactly the code the inline
path runs (the reference-side functions of ``gate_a``, ``gate_c``,
``audit.run`` and ``audit.lethe_contracts``), and writes an **entry** here. A
**consumer** item (the candidate's gate or channel item) draws its inputs as
before, loads the entry instead of recomputing, runs the candidate and
compares exactly as before. The store is an optimisation only: whenever an
entry is missing, unreadable, made under other conditions or marked unusable,
the consumer computes inline (the code path every pilot verdict came from).

An entry is usable only when the reference side cannot have influenced the
candidate's run except through the values stored. The reference item checks,
for every reference call, that

- no input tensor it received changed (byte comparison with a clone taken
  before the call), because the inline path passes the same tensors to the
  candidate afterwards;
- the CPU and CUDA random-number states are unchanged, because the inline
  path runs the candidate with the state the reference left;
- no stored output shares storage with an input (a stored copy would not
  follow a later in-place write);
- every output is a tensor or a tuple or list of tensors (what is stored);

and the key binds the problem source, the replicate, the channel's
configuration, the device type, torch's version, the TF32/cuDNN switches and
default dtype in force, and the gate or audit code hash. The consumer
re-checks the switches before every draw and computes the remaining draws
inline if a candidate changed them. With those conditions the consumer's rows
equal the inline rows whenever the inline path is itself reproducible
(``tests/test_q1_refstore_equivalence.py``); timing fields differ.

Layout: ``ROOT/<channel>/<key>/entry.json`` and one ``draw-NNN.pt`` per stored
draw (``torch.save``; loaded with ``mmap=True, weights_only=True``). An entry
directory is written under a temporary name and renamed into place, so a
reader never sees a partial entry. Consumers record what they used in
``ROOT/uses/`` (one small JSON file per item attempt), never in verdict rows.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STORE_SCHEMA = "q1-refstore/1"
#: Reference gate id -> channel.
REFERENCE_GATES: dict[str, str] = {
    "ref_a": "a",
    "ref_a_head": "a_head",
    "ref_c": "c",
    "ref_A1": "A1",
    "ref_A2": "A2",
    "ref_A3": "A3",
    "ref_A5": "A5",
}
CHANNEL_GATE = {channel: gate for gate, channel in REFERENCE_GATES.items()}
#: Channel -> the consumer gates that read its entries.
CONSUMERS: dict[str, tuple[str, ...]] = {
    "a": ("a", "a_1e-3", "a_static"),
    "a_head": ("a_head_1e-4", "a_head_1e-2"),
    "c": ("c",),
    "A1": ("A1",),
    "A2": ("A2",),
    "A3": ("A3",),
    "A5": ("A5",),
}
CHANNEL_OF: dict[str, str] = {gate: ch for ch, gates in CONSUMERS.items() for gate in gates}
AUDIT_CHANNELS = ("A1", "A2", "A3", "A5")
#: The journal reference items write to (beside the scoring journal).
REFERENCE_JOURNAL = "references.jsonl"
#: Item-option key naming the store root on a consumer or reference item.
OPTION = "reference_store"


def is_reference_gate(gate: str) -> bool:
    return gate in REFERENCE_GATES


def reference_kernel_id(problem_id: str) -> str:
    """Pseudo kernel id of a problem's reference items (``schema.KERNEL_ID_RE``)."""
    return "reference." + problem_id.replace("/", "-")


# --- keys ------------------------------------------------------------------------


def environment_facts() -> dict[str, Any]:
    """Process-wide switches that change what a reference computes."""
    import torch

    return {
        "matmul_allow_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
        "cudnn_allow_tf32": bool(torch.backends.cudnn.allow_tf32),
        "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
        "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
        "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
        "float32_matmul_precision": torch.get_float32_matmul_precision(),
        "default_dtype": str(torch.get_default_dtype()),
    }


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def code_sha256(channel: str) -> str:
    from harness.q1.versions import audit_code_sha256, gate_code_sha256

    return audit_code_sha256() if channel in AUDIT_CHANNELS else gate_code_sha256()


def key_payload(
    channel: str,
    *,
    problem_id: str,
    problem_source: str,
    seed: int,
    device_type: str,
    params: Mapping[str, Any],
) -> dict[str, Any]:
    """Everything an entry's values depend on, apart from the switches in
    :func:`environment_facts` (recorded per draw and re-checked by consumers)."""
    import torch

    if channel not in CONSUMERS:
        raise ValueError(f"unknown reference channel {channel}")
    return {
        "schema": STORE_SCHEMA,
        "channel": channel,
        "problem_id": problem_id,
        "problem_sha256": hashlib.sha256(problem_source.encode("utf-8")).hexdigest(),
        "seed": int(seed),
        "device_type": device_type,
        "torch": torch.__version__,
        "code_sha256": code_sha256(channel),
        "params": json.loads(_canonical(dict(params))),
    }


def key_of(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


# --- side-effect probe -----------------------------------------------------------


def _tensors(value: Any) -> list[Any]:
    import torch

    if isinstance(value, torch.Tensor):
        return [value]
    if isinstance(value, list | tuple):
        return [t for item in value for t in _tensors(item)]
    return []


def rng_state(device: Any) -> list[Any]:
    import torch

    states = [torch.get_rng_state()]
    if getattr(device, "type", str(device)) == "cuda":
        states.append(torch.cuda.get_rng_state(device))
    return states


class Probe:
    """Byte clones of the tensors a reference call receives and the RNG state.

    ``changes()`` after the call lists what it altered (empty: nothing)."""

    def __init__(self, values: Any, device: Any) -> None:
        self.device = device
        self.originals = _tensors(values)
        self.clones = [t.detach().clone() for t in self.originals]
        self.rng = [s.clone() for s in rng_state(device)]

    def changes(self) -> list[str]:
        import torch

        from harness.q1.gates.reductions import bytes_equal

        out: list[str] = []
        for index, (now, before) in enumerate(zip(self.originals, self.clones, strict=True)):
            if (
                now.dtype != before.dtype
                or tuple(now.shape) != tuple(before.shape)
                or not bytes_equal(now, before)
            ):
                out.append(f"reference-mutated-input-{index}")
        after = rng_state(self.device)
        if len(after) != len(self.rng) or not all(
            torch.equal(a, b) for a, b in zip(after, self.rng, strict=True)
        ):
            out.append("reference-changed-rng-state")
        return out


def _span(t: Any) -> tuple[int, int]:
    storage = t.untyped_storage()
    start = storage.data_ptr()
    return start, start + storage.nbytes()


def storable(value: Any) -> bool:
    """A tensor, or a tuple or list (nested) of tensors."""
    import torch

    if isinstance(value, torch.Tensor):
        return True
    if isinstance(value, list | tuple):
        return all(storable(item) for item in value)
    return False


def aliases(outputs: Any, inputs: Any) -> bool:
    """Whether any output tensor shares storage with any input tensor."""
    spans = [_span(t) for t in _tensors(inputs) if t.numel() > 0]
    for out in _tensors(outputs):
        if out.numel() == 0:
            continue
        a = _span(out)
        if any(a[0] < b[1] and b[0] < a[1] for b in spans):
            return True
    return False


def to_cpu(value: Any) -> Any:
    """Detached CPU copy of tensors in a tensor, tuple, list or dict (structure kept)."""
    import torch

    if isinstance(value, torch.Tensor):
        return value.detach().to("cpu")
    if isinstance(value, tuple):
        return tuple(to_cpu(v) for v in value)
    if isinstance(value, list):
        return [to_cpu(v) for v in value]
    if isinstance(value, dict):
        return {k: to_cpu(v) for k, v in value.items()}
    return value


def to_device(value: Any, device: Any) -> Any:
    import torch

    if isinstance(value, torch.Tensor):
        return value.to(device)
    if isinstance(value, tuple):
        return tuple(to_device(v, device) for v in value)
    if isinstance(value, list):
        return [to_device(v, device) for v in value]
    if isinstance(value, dict):
        return {k: to_device(v, device) for k, v in value.items()}
    return value


#: Text of a CUDA or host resource failure. Such an exception depends on what else
#: holds memory, so a reference item that meets one never stores it as the
#: reference's outcome: the entry is unusable and consumers compute inline.
RESOURCE_MARKERS = (
    "outofmemoryerror",
    "out of memory",
    "cudaerrormemoryallocation",
    "cuda_error_out_of_memory",
    "cannot allocate memory",
)


def resource_failure(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return isinstance(exc, MemoryError) or any(marker in text for marker in RESOURCE_MARKERS)


def checked_call(
    call: Callable[[], Any], values: Any, device: Any, problems: list[str], *, store: Any = None
) -> Any:
    """Run one reference-side call under a :class:`Probe`; append what disqualifies
    its result from reuse to ``problems``. ``store`` (default: the call's result)
    is the value a consumer would read; it must be storable and not alias ``values``."""
    probe = Probe(values, device)
    result = call()
    problems.extend(probe.changes())
    stored = result if store is None else store(result)
    if stored is not None:
        if not storable(stored):
            problems.append("reference-output-not-storable")
        elif aliases(stored, values):
            problems.append("reference-output-aliases-input")
    return result


# --- writing ------------------------------------------------------------------------


@dataclass
class Draw:
    """One stored draw: JSON metadata and, optionally, a torch-saved object."""

    meta: dict[str, Any]
    payload: Any = None


@dataclass
class Built:
    """What a channel's reference function produced."""

    draws: list[Draw]
    problems: list[str] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)


def entry_dir(root: Path, channel: str, key: str) -> Path:
    return Path(root) / channel / key


def write_entry(root: Path, payload: Mapping[str, Any], built: Built) -> dict[str, Any]:
    """Write an entry atomically; returns its manifest. An existing complete entry
    for the same key is kept (a concurrent or earlier writer won)."""
    import torch

    channel = payload["channel"]
    key = key_of(payload)
    final = entry_dir(root, channel, key)
    if (final / "entry.json").exists():
        return json.loads((final / "entry.json").read_text(encoding="utf-8"))
    final.parent.mkdir(parents=True, exist_ok=True)
    temp = final.parent / f".{key}.{os.getpid()}.{time.time_ns()}.tmp"
    temp.mkdir()
    draws = []
    total = 0
    try:
        for index, draw in enumerate(built.draws):
            meta = dict(draw.meta)
            if draw.payload is not None:
                name = f"draw-{index:03d}.pt"
                torch.save(draw.payload, temp / name)
                size = (temp / name).stat().st_size
                meta["file"] = name
                meta["bytes"] = size
                total += size
            draws.append(meta)
        manifest = {
            "schema": STORE_SCHEMA,
            "key": key,
            "payload": dict(payload),
            "usable": not built.problems,
            "problems": list(built.problems),
            "facts": dict(built.facts),
            "draws": draws,
            "bytes": total,
            "written_at": round(time.time(), 3),
        }
        (temp / "entry.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        try:
            os.rename(temp, final)
        except OSError:
            if (final / "entry.json").exists():
                shutil.rmtree(temp, ignore_errors=True)
                return json.loads((final / "entry.json").read_text(encoding="utf-8"))
            raise
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return manifest


# --- reading -------------------------------------------------------------------------


@dataclass
class Taken:
    """One draw read from an entry: ``kind`` is ``ok`` (``value`` on the device) or
    ``raised`` (``error`` holds the reference's ``exception_details``)."""

    kind: str
    meta: dict[str, Any]
    value: Any = None
    error: dict[str, str] = field(default_factory=dict)


class Entry:
    """A verified, usable entry. ``take(i, device)`` returns draw ``i`` or ``None``,
    after which the consumer computes this and every later draw inline: the
    switches changed since the entry was written (a candidate set them), or the
    draw could not be read. A store fault is therefore never a verdict."""

    def __init__(self, path: Path, manifest: Mapping[str, Any]) -> None:
        self.path = path
        self.manifest = dict(manifest)
        self.draws: list[dict[str, Any]] = list(manifest["draws"])

    def facts_hold(self) -> bool:
        return environment_facts() == self.manifest["facts"]

    def load(self, index: int, device: Any) -> Any:
        import torch

        meta = self.draws[index]
        file = self.path / meta["file"]
        if file.stat().st_size != int(meta["bytes"]):
            raise OSError(f"reference store file {file} has the wrong size")
        value = torch.load(file, map_location="cpu", mmap=True, weights_only=True)
        return to_device(value, device)

    def take(self, index: int, device: Any) -> Taken | None:
        if not self.facts_hold():
            note(inline_from_draw=index, inline_reason="switches-changed")
            return None
        try:
            meta = self.draws[index]
            if meta["kind"] == "raised":
                return Taken("raised", meta, error=dict(meta["error"]))
            value = self.load(index, device) if "file" in meta else None
        except Exception as exc:  # a store fault: compute inline from here on
            note(inline_from_draw=index, inline_reason=f"read-failed: {type(exc).__name__}")
            return None
        return Taken("ok", meta, value=value)


#: What this process looked up (the worker writes it to ``ROOT/uses/``).
USES: list[dict[str, Any]] = []


def _complete(
    manifest: Mapping[str, Any], path: Path, draws: int | None, ends_at_raise: bool
) -> bool:
    listed = list(manifest.get("draws", []))
    if draws is not None:
        short = ends_at_raise and listed and listed[-1].get("kind") == "raised"
        if not (len(listed) == draws or (short and len(listed) < draws)):
            return False
    for meta in listed:
        if meta.get("kind") not in {"ok", "raised"}:
            return False
        if "file" in meta:
            try:
                if (path / meta["file"]).stat().st_size != int(meta["bytes"]):
                    return False
            except OSError:
                return False
    return True


def lookup(
    root: str | os.PathLike[str] | None,
    payload: Mapping[str, Any],
    *,
    draws: int | None = None,
    ends_at_raise: bool = False,
) -> Entry | None:
    """The usable entry for ``payload`` under ``root``, or ``None`` (compute inline).

    ``draws`` is the number of draws the consumer will take; ``ends_at_raise``
    allows fewer when the last one raised (gate (a) stops at a raised trial)."""
    if not root:
        return None
    key = key_of(payload)
    record: dict[str, Any] = {"channel": payload["channel"], "key": key}
    USES.append(record)
    path = entry_dir(Path(root), payload["channel"], key)
    try:
        manifest = json.loads((path / "entry.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        record["used"], record["reason"] = False, "no-entry"
        return None
    if manifest.get("schema") != STORE_SCHEMA or manifest.get("key") != key:
        record["used"], record["reason"] = False, "entry-mismatch"
        return None
    if manifest.get("payload") != json.loads(_canonical(dict(payload))):
        record["used"], record["reason"] = False, "payload-mismatch"
        return None
    if not manifest.get("usable"):
        record["used"], record["reason"] = False, "entry-unusable"
        record["problems"] = list(manifest.get("problems", []))
        return None
    if not _complete(manifest, path, draws, ends_at_raise):
        record["used"], record["reason"] = False, "entry-incomplete"
        return None
    entry = Entry(path, manifest)
    if not entry.facts_hold():
        record["used"], record["reason"] = False, "switches-differ"
        return None
    record["used"], record["reason"] = True, ""
    record["draws"] = len(entry.draws)
    return entry


def note(**facts: Any) -> None:
    """Add facts to the latest lookup record (e.g. draws computed inline after a switch)."""
    if USES:
        USES[-1].update(facts)


def write_uses(root: str | os.PathLike[str] | None, item: Mapping[str, Any]) -> None:
    """Best effort: one JSON file per item attempt under ``ROOT/uses/``."""
    if not root or not USES:
        return
    with contextlib.suppress(OSError):
        folder = Path(root) / "uses"
        folder.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha256(str(item.get("item_key")).encode()).hexdigest()[:24]
        record = {
            "item_key": item.get("item_key"),
            "attempt": item.get("attempt"),
            "gate": item.get("gate"),
            "lookups": USES,
        }
        temp = folder / f".{name}.{os.getpid()}.tmp"
        temp.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        os.replace(temp, folder / f"{name}-a{item.get('attempt', 1)}.json")


def read_uses(root: str | os.PathLike[str]) -> list[dict[str, Any]]:
    folder = Path(root) / "uses"
    if not folder.is_dir():
        return []
    out = []
    for path in sorted(folder.glob("*.json")):
        with contextlib.suppress(OSError, ValueError):
            out.append(json.loads(path.read_text(encoding="utf-8")))
    return out


# --- reference items ------------------------------------------------------------------


def reference_outcome(item: Mapping[str, Any]) -> list[Any]:
    """Run a reference item (worker entry point): compute and write the entry.

    No candidate code runs here. The single row's verdict is ``accept`` when a
    usable entry exists afterwards and ``error`` otherwise (with the reasons)."""
    from harness.q1 import problems as problem_lib
    from harness.q1.gates.common import GateOutcome, exception_details, resolve_device

    start = time.perf_counter()
    gate = item["gate"]
    channel = REFERENCE_GATES[gate]
    seed = int(item["seed"])
    options = dict(item.get("options", {}))
    root = options.get(OPTION)
    if not root:
        raise ValueError(f"{gate} needs options.{OPTION}")
    device = resolve_device(item.get("device"))
    problem_id = item["problem_id"]
    details: dict[str, Any] = {"channel": channel, "store_root": str(root)}
    try:
        if item.get("problem_source_path"):
            problem_source = Path(item["problem_source_path"]).read_text(encoding="utf-8")
        else:
            problem_source = problem_lib.load_problem_source(problem_id)
        payload, compute = _channel(channel, item, problem_id, problem_source, seed, device)
        key = key_of(payload)
        details["key"] = key
        existing = entry_dir(Path(root), channel, key) / "entry.json"
        if existing.exists():
            manifest = json.loads(existing.read_text(encoding="utf-8"))
            details["existing"] = True
        else:
            facts = environment_facts()
            built = compute()
            built.facts = facts
            if environment_facts() != facts:
                built.problems.append("switches-changed-during-reference")
            manifest = write_entry(Path(root), payload, built)
            details["existing"] = False
        details.update(
            {
                "usable": bool(manifest["usable"]),
                "problems": list(manifest["problems"]),
                "draws": len(manifest["draws"]),
                "bytes": int(manifest["bytes"]),
            }
        )
        verdict = "accept" if manifest["usable"] else "error"
        if not manifest["usable"]:
            details["reason"] = "entry-unusable"
    except Exception as exc:
        verdict = "error"
        details.update({"reason": "reference-item-failed", **exception_details(exc)})
    return [
        GateOutcome(
            gate,
            f"reference/seed-{seed}",
            verdict,
            details=details,
            wall_seconds=time.perf_counter() - start,
        )
    ]


def _channel(
    channel: str,
    item: Mapping[str, Any],
    problem_id: str,
    problem_source: str,
    seed: int,
    device: Any,
) -> tuple[dict[str, Any], Callable[[], Built]]:
    """(key payload, compute function) for a reference item, from the same helpers
    the consumers use."""
    options = dict(item.get("options", {}))
    if channel in {"a", "a_head"}:
        from harness.q1.gates import gate_a

        variant = "a" if channel == "a" else "a_head_1e-4"
        num_trials = int(options.get("num_trials", 5))
        payload = gate_a.reference_payload(
            problem_id,
            problem_source,
            variant=variant,
            seed=seed,
            num_trials=num_trials,
            device=device,
        )
        return payload, lambda: gate_a.reference_trials(
            problem_source, variant=variant, seed=seed, num_trials=num_trials, device=device
        )
    if channel == "c":
        from harness.q1.gates import gate_c

        manifest = _manifest(options)
        specs = gate_c.c_configs(problem_id, replicate_seed=seed, manifest=manifest)
        payload = gate_c.reference_payload(
            problem_id, problem_source, replicate_seed=seed, device=device, specs=specs
        )
        return payload, lambda: gate_c.reference_configs(
            problem_id, problem_source, replicate_seed=seed, device=device, manifest=manifest
        )
    from harness.q1.audit import run as audit

    entry = _manifest(options)["problems"].get(problem_id, {}) if channel == "A3" else None
    payload = audit.reference_payload(
        channel,
        problem_id,
        problem_source,
        replicate_seed=seed,
        device=device,
        manifest_entry=entry,
    )
    return payload, lambda: audit.reference_draws(
        channel,
        problem_id,
        problem_source,
        replicate_seed=seed,
        device=device,
        manifest_entry=entry,
    )


def _manifest(options: Mapping[str, Any]) -> Mapping[str, Any]:
    from harness.q1.gates.gate_c import shape_manifest

    if options.get("manifest_path"):
        return json.loads(Path(options["manifest_path"]).read_text(encoding="utf-8"))
    return shape_manifest()


__all__ = [
    "AUDIT_CHANNELS",
    "Built",
    "CHANNEL_GATE",
    "CHANNEL_OF",
    "CONSUMERS",
    "Draw",
    "Entry",
    "OPTION",
    "Probe",
    "REFERENCE_GATES",
    "REFERENCE_JOURNAL",
    "STORE_SCHEMA",
    "Taken",
    "USES",
    "aliases",
    "checked_call",
    "entry_dir",
    "environment_facts",
    "is_reference_gate",
    "key_of",
    "key_payload",
    "lookup",
    "note",
    "read_uses",
    "reference_kernel_id",
    "resource_failure",
    "reference_outcome",
    "rng_state",
    "storable",
    "to_cpu",
    "to_device",
    "write_entry",
    "write_uses",
]
