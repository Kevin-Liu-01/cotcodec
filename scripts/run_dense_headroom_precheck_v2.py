#!/usr/bin/env python3
"""GPU entry point of q3-dense-headroom-precheck-v2 (program decision D36).

v1's entry point (``scripts/run_dense_headroom_precheck.py``) with v1's data,
statistics, decision rules and thresholds unchanged (the data and statistics
modules are imported byte for byte), and three repairs:

1. Signals. SIGUSR1 and SIGTERM are blocked in every thread from the first
   line of this file, so no library can intercept them; ``SignalGuard``
   (``harness/dense_headroom_v2.py``) consumes them at every unit and chunk
   boundary and re-installs CPython's handler whenever a library replaced it
   (LLVM inside Triton does so at the first kernel compile, which is why v1's
   4B job ignored Slurm's SIGUSR1). Between chunks a received signal still
   means: completed chunks are on disk, ``receipt-interrupted.json`` is
   written, then the checkpoint marker (``trigger=SIG<name>``), exit 75.
2. Job binding. Every receipt records ``slurm_job_id`` from the job's
   ``job.env`` (the batch script writes it into the job's run directory, the
   container's ``/outputs``, before the container starts); under the batch
   script a job without it exits 2 before any work.
3. The evaluation runs ``harness/dense_headroom_torch_v2.py`` (equal to v1's
   on every computed quantity).

Profiles: ``registered`` (the lanes; the frozen preregistration and its code
table are verified at start-up), ``tiny`` (the CPU doctor) and ``timing``
(the one development timing job of D36, before the freeze: the 4B lane's
model and inputs, the registered subset of development units in round-robin
stage order with per-unit component timings, a v1-path reference on the
first units of each stage compared bit for bit, then the lane's other chunks
until a signal, which it answers exactly as a lane does; it writes
``timing-receipt.json`` and never a lane receipt).

Exit codes: 0 complete, 2 startup contract, 3 integrity, 75 interrupted after
a confirmed save.
"""

from __future__ import annotations

import signal as _signal

# First, before any import that can start a thread: every thread inherits this
# mask, so SIGUSR1 and SIGTERM stay pending until the guard consumes them.
if hasattr(_signal, "pthread_sigmask"):
    _signal.pthread_sigmask(_signal.SIG_BLOCK, {_signal.SIGUSR1, _signal.SIGTERM})

import argparse  # noqa: E402
import cProfile  # noqa: E402
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import pstats  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import traceback  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

PROCESS_STARTED = time.perf_counter()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402

from harness import dense_headroom_data as dhd  # noqa: E402
from harness import dense_headroom_stats as dhs  # noqa: E402
from harness import dense_headroom_v2 as dv2  # noqa: E402
from harness import dense_headroom_v2_lanes as lanes  # noqa: E402

EXIT_OK = 0
EXIT_CONTRACT = 2
EXIT_INTEGRITY = 3
EXIT_CHECKPOINTED = 75
CHUNK_UNITS = 16
TINY_REPLICATES = 200
OUTPUT_SUBDIR = dhd.OUTPUT_SUBDIR
TIMING_RECEIPT = "timing-receipt.json"
TIMING_REFERENCE_UNITS_PER_STAGE = 1
CODE_FILES = (
    "scripts/run_dense_headroom_precheck_v2.py",
    "scripts/preregister.py",
    "harness/dense_headroom_v2.py",
    "harness/dense_headroom_v2_lanes.py",
    "harness/dense_headroom_torch_v2.py",
    "harness/dense_headroom_data.py",
    "harness/dense_headroom_stats.py",
    "harness/dense_headroom_torch.py",
    "harness/sparse_indexer_torch.py",
    "harness/sparse_indexer_bank.py",
    "harness/sparse_indexer_k1_runtime.py",
    "harness/sparse_indexer_k1_marker.py",
    "harness/sparse_indexer_k1_stats.py",
    "harness/sparse_indexer_data.py",
    "harness/translation_supervised_indexer.py",
)
_TABLE_ROW = re.compile(r"^\| ([A-Za-z0-9_./-]+\.(?:py|yaml)) \| ([0-9a-f]{64}) \|$")


class StartupError(RuntimeError):
    """A fail-closed startup check failed (exit code 2)."""


class Interrupted(Exception):  # noqa: N818 - control flow, not an error
    """A signal arrived; completed chunks are on disk."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    # allow_abbrev=False: a prefix such as --see must never reach the seed option.
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--expected-evidence-sha256", required=True)
    parser.add_argument("--source-tokenizer", type=Path, default=None)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--expected-receipt-sha256", required=True)
    parser.add_argument("--preregistration", type=Path, default=None)
    parser.add_argument("--expected-preregistration-sha256", default=None)
    parser.add_argument("--experiment-id", default=dv2.EXPERIMENT_ID)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--ledger-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--profile", choices=("registered", "tiny", "timing"),
                        default="registered")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    return parser.parse_args(argv)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_hashes() -> dict[str, str]:
    return {name: sha256_file(PROJECT_ROOT / name) for name in CODE_FILES}


def tabled_code(preregistration_text: str) -> dict[str, str]:
    """The preregistration's code table (``| path | sha256 |`` rows)."""

    rows = {}
    for line in preregistration_text.splitlines():
        match = _TABLE_ROW.match(line.strip())
        if match:
            rows[match.group(1)] = match.group(2)
    return rows


def prepare_runtime(output_dir: Path, device: str) -> None:
    """Before torch is imported: JIT caches on the run directory, and on CPU no
    flash-linear-attention (its Triton kernels need a GPU; transformers then
    uses its torch implementation of the gated delta rule)."""

    cache = output_dir / "cache"
    os.environ.setdefault("TRITON_CACHE_DIR", str(cache / "triton"))
    os.environ.setdefault("TRITON_HOME", str(cache / "triton-home"))
    os.environ.setdefault("TORCHINDUCTOR_CACHE_DIR", str(cache / "inductor"))
    if device == "cpu":
        dhd.block_gpu_only_kernels()


def make_codecs(args: argparse.Namespace, lane: dhd.Lane) -> tuple[Any, Any]:
    if lane.profile == "tiny":
        source = dhd.StandInByteCodec()
        return source, (dhd.StandInPairCodec() if lane.retokenize else source)
    if args.source_tokenizer is None:
        raise StartupError("a registered lane needs --source-tokenizer")
    source = dhd.ByteLevelCodec(args.source_tokenizer)
    lane_codec = dhd.ByteLevelCodec(args.model_dir / "tokenizer.json")
    return source, lane_codec


def lane_for(args: argparse.Namespace) -> dhd.Lane:
    try:
        lane = lanes.lane_of(args.lane)
    except dhd.DenseDataError as exc:
        raise StartupError(str(exc)) from exc
    if args.profile == "timing":
        # The 4B lane on the GPU; the tiny hybrid only in the CPU doctor.
        if lane.lane_id not in (lanes.TIMING_LANE, "tiny-hybrid"):
            raise StartupError(f"the timing profile runs only {lanes.TIMING_LANE}")
        return lane
    if lane.profile != args.profile:
        raise StartupError(f"lane {lane.lane_id} belongs to the {lane.profile} profile")
    return lane


def startup_checks(args: argparse.Namespace) -> tuple[dict[str, Any], dhd.Lane, dict[str, Any],
                                                      Any, Any]:
    """Fail closed before any work; returns (bundle, lane, hashes, source, lane codec)."""

    from harness import sparse_indexer_data as sid
    from scripts import preregister

    if args.experiment_id != dv2.EXPERIMENT_ID:
        raise StartupError(f"experiment id must be {dv2.EXPERIMENT_ID}")
    if args.seeds != list(dhd.SEEDS):
        raise StartupError(f"seeds must be {list(dhd.SEEDS)}")
    lane = lane_for(args)
    registered_inputs = lane.profile == "registered"
    if registered_inputs and args.expected_evidence_sha256 != dhd.SOURCE_BUNDLE_SHA256:
        raise StartupError("a registered lane reads only the K1 bundle 919d016b...")
    output_root = os.environ.get("COTCODEC_OUTPUT_DIR")
    if (registered_inputs or args.profile == "timing") and not output_root:
        raise StartupError("the registered and timing profiles run only under the batch "
                           "script (COTCODEC_OUTPUT_DIR and its manifest.json and job.env)")
    try:
        binding = dv2.batch_job_id(Path(output_root) if output_root else None, os.environ)
    except dv2.JobBindingError as exc:
        raise StartupError(str(exc)) from exc
    try:
        bundle = sid.load_bundle(args.evidence, args.expected_evidence_sha256)
    except (OSError, sid.DataContractError) as exc:
        raise StartupError(f"bundle check failed: {exc}") from exc
    code = code_hashes()
    prereg_sha: str | None = None
    row_hash: str | None = None
    if args.profile != "timing":
        if args.preregistration is None or args.expected_preregistration_sha256 is None:
            raise StartupError("the lanes need --preregistration and its expected digest")
        prereg_sha = sha256_file(args.preregistration)
        if prereg_sha != args.expected_preregistration_sha256:
            raise StartupError("preregistration sha256 differs from the expected digest")
        try:
            row = preregister.verify(args.experiment_id, ledger=args.ledger
                                     or preregister.DEFAULT_LEDGER, root=args.ledger_root)
        except preregister.PreregistrationError as exc:
            raise StartupError(f"preregistration ledger check failed: {exc}") from exc
        if row["sha256"] != prereg_sha:
            raise StartupError("ledger row digest differs from the preregistration file")
        row_hash = str(row["hash"])
        if registered_inputs:
            table = tabled_code(args.preregistration.read_text(encoding="utf-8"))
            differing = sorted(name for name in CODE_FILES if table.get(name) != code[name])
            if differing:
                raise StartupError(f"code differs from the preregistration's table: {differing}")
    elif args.preregistration is not None or args.expected_preregistration_sha256 is not None:
        raise StartupError("the timing job runs before the freeze and reads no preregistration")
    receipt_sha = sha256_file(args.receipt)
    if receipt_sha != args.expected_receipt_sha256:
        raise StartupError("model receipt sha256 differs from the expected digest")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if receipt.get("model_id") != lane.model_id or receipt.get("revision") != lane.revision:
        raise StartupError("the model receipt is not the lane's model and revision")
    try:
        source, lane_codec = make_codecs(args, lane)
    except (OSError, dhd.DenseDataError) as exc:
        raise StartupError(f"tokenizer check failed: {exc}") from exc
    if registered_inputs:
        if receipt_sha != lane.receipt_sha256:
            raise StartupError("the model receipt is not the registered receipt")
        if receipt.get("artifact_root_sha256") != lane.artifact_root_sha256:
            raise StartupError("the model artifact root is not the registered one")
        listed = {f.get("path"): f.get("sha256") for f in receipt.get("files", [])
                  if isinstance(f, dict)}
        if listed.get("tokenizer.json") != lane.tokenizer_sha256:
            raise StartupError("the receipt's tokenizer.json is not the registered one")
        if lane_codec.sha256 != lane.tokenizer_sha256:
            raise StartupError("the model directory's tokenizer.json differs from the receipt")
        if source.sha256 != dhd.SOURCE_TOKENIZER_SHA256:
            raise StartupError("--source-tokenizer is not the bundle's tokenizer")
    if bundle.get("tokenizer_sha256") != source.sha256:
        raise StartupError("the bundle was not built with the source tokenizer")
    job = {"kind": "unmanaged", "predecessor_job_id": None, "minutes": None}
    if output_root:
        job = check_batch_manifest(Path(output_root), lane, args.seeds, receipt_sha,
                                   args.expected_evidence_sha256,
                                   args.output_dir / "checkpoints", args.profile)
    if args.device == "cuda":
        import torch

        if torch.cuda.device_count() < 1:
            raise StartupError("no GPU is visible")
        expected = os.environ.get("COTCODEC_EXPECTED_GPUS")
        if expected is not None and torch.cuda.device_count() != int(expected):
            raise StartupError(f"{torch.cuda.device_count()} visible GPUs, expected {expected}")
    hashes = {
        "bundle_sha256": args.expected_evidence_sha256,
        "preregistration_sha256": prereg_sha,
        "ledger_row_hash": row_hash,
        "receipt_sha256": receipt_sha,
        "source_tokenizer_sha256": source.sha256,
        "lane_tokenizer_sha256": lane_codec.sha256,
        "git_sha": os.environ.get("COTCODEC_GIT_SHA", "unknown"),
        "source_sha256": os.environ.get("COTCODEC_SOURCE_SHA256", "unknown"),
        "code": code,
        "job": {**job, "slurm_job_id": binding["slurm_job_id"],
                "slurm_job_id_source": binding["source"]},
    }
    return bundle, lane, hashes, source, lane_codec


def check_batch_manifest(output_root: Path, lane: dhd.Lane, seeds: list[int], receipt_sha: str,
                         evidence_sha: str, checkpoints: Path, profile: str) -> dict[str, Any]:
    """The batch manifest of this job against argv and the registered lane.

    Returns the job's kind (``fresh`` or ``continuation``), its predecessor and
    its minutes. Raises ``StartupError`` on a manifest the filler cannot have
    produced. The timing job is always fresh, with the timing limit.
    """

    manifest_path = output_root / "manifest.json"
    if not manifest_path.is_file():
        raise StartupError("the batch manifest is missing from the output root")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("seeds") != seeds:
        raise StartupError("manifest seeds differ from argv seeds")
    if manifest.get("model", {}).get("receipt_sha256") != receipt_sha:
        raise StartupError("manifest receipt digest differs")
    if manifest.get("study_artifact", {}).get("sha256") != evidence_sha:
        raise StartupError("manifest study artifact digest differs")
    predecessor = manifest.get("resume_from_job_id")
    resume_receipt = output_root / "resume-receipt.json"
    if predecessor is None:
        if manifest.get("resume_subpath") is not None or resume_receipt.exists():
            raise StartupError("resume fields or a resume receipt without a predecessor")
        if checkpoints.exists():
            raise StartupError("a fresh job found checkpoints it did not write")
        kind = "fresh"
    else:
        if profile == "timing":
            raise StartupError("the timing job is never a continuation")
        predecessor = str(predecessor)
        if manifest.get("resume_subpath") != dhd.RESUME_SUBPATH:
            raise StartupError(f"a continuation resumes only {dhd.RESUME_SUBPATH}")
        if not resume_receipt.is_file():
            raise StartupError("a continuation without the batch script's resume receipt")
        copied = json.loads(resume_receipt.read_text(encoding="utf-8"))
        if (str(copied.get("predecessor_job_id")) != predecessor
                or copied.get("resume_subpath") != dhd.RESUME_SUBPATH):
            raise StartupError("the resume receipt names another predecessor or subpath")
        if not (checkpoints / "dev-artifact.sha256").is_file():
            raise StartupError("the continuation found no pinned development artifact")
        kind = "continuation"
    minutes = manifest.get("minutes")
    if profile == "timing":
        if manifest.get("gpus") != lane.gpus or minutes != lanes.TIMING_MINUTES:
            raise StartupError(f"the timing job runs on {lane.gpus} GPU for "
                               f"{lanes.TIMING_MINUTES} minutes")
    elif lane.profile == "registered":
        if manifest.get("gpus") != lane.gpus:
            raise StartupError("manifest GPUs differ from the registered lane")
        top = lane.minutes - (dhd.CONTINUATION_MIN_CHARGE if kind == "continuation" else 0)
        if (not isinstance(minutes, int) or isinstance(minutes, bool)
                or not dhd.MIN_JOB_MINUTES <= minutes <= top):
            raise StartupError(f"manifest minutes {minutes!r} are outside the lane's "
                               f"{dhd.MIN_JOB_MINUTES}..{top} for a {kind} job")
    return {"kind": kind, "predecessor_job_id": predecessor, "minutes": minutes}


# --------------------------------------------------------------------------- #
# Evaluation loop
# --------------------------------------------------------------------------- #


def chunk_name(unit_ids: list[str]) -> str:
    return hashlib.sha256("|".join(unit_ids).encode()).hexdigest()[:16]


def save_chunk(path: Path, unit_ids: list[str], records: list[dict[str, Any]],
               names: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}.npz")
    np.savez(temporary, unit_ids=np.asarray(unit_ids), selectors=np.asarray(names),
             recall=np.stack([r["recall"] for r in records]),
             ties=np.stack([r["ties"] for r in records]),
             max_selected=np.asarray([r["max_selected"] for r in records], dtype=np.int64),
             k_blocks=np.asarray([r["k_blocks"] for r in records], dtype=np.int64),
             mc_scores=np.stack([r["mc_scores"] for r in records]),
             mc_correct=np.asarray([r["mc_correct"] for r in records], dtype=np.int64))
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def collect(eval_dir: Path, names: list[str]) -> dhs.Results:
    units: dict[str, dict[str, Any]] = {}
    for path in sorted(eval_dir.glob("*/chunk-*.npz")):
        with np.load(path, allow_pickle=False) as data:
            if [str(v) for v in data["selectors"]] != names:
                raise dhs.DenseStatsError(f"{path.name}: selectors differ from the registered")
            for i, unit_id in enumerate(data["unit_ids"]):
                unit_id = str(unit_id)
                if unit_id in units:
                    raise dhs.DenseStatsError(f"unit {unit_id} evaluated twice")
                units[unit_id] = {"recall": np.asarray(data["recall"][i], dtype=np.float64),
                                  "ties": np.asarray(data["ties"][i]),
                                  "max_selected": int(data["max_selected"][i]),
                                  "k_blocks": int(data["k_blocks"][i]),
                                  "mc_scores": np.asarray(data["mc_scores"][i],
                                                          dtype=np.float64),
                                  "mc_correct": int(data["mc_correct"][i])}
    return dhs.Results(selectors=list(names), units=units)


class Job:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.out = args.output_dir
        self.ckpt = self.out / "checkpoints"
        self.marker = Path(os.environ.get("COTCODEC_CHECKPOINT_MARKER",
                                          str(self.out.parent / "checkpoint.ready")))
        self.timings: dict[str, Any] = {}
        self.hashes: dict[str, Any] = {}
        self.guard = dv2.SignalGuard()
        self.lane: dhd.Lane | None = None

    def receipt(self, name: str, payload: dict[str, Any]) -> str:
        job = self.hashes.get("job", {})
        payload = {**payload, "experiment_id": self.args.experiment_id,
                   "lane": self.lane.as_dict() if self.lane else None,
                   "profile": self.args.profile, "seeds": list(self.args.seeds),
                   "hashes": self.hashes, "timings_s": self.timings,
                   "signals": self.guard.as_dict(),
                   "slurm_job_id": job.get("slurm_job_id"),
                   "slurm_job_id_source": job.get("slurm_job_id_source")}
        return dhd.write_json(self.out / name, _jsonable(payload))

    def run(self) -> int:
        args = self.args
        self.out.mkdir(parents=True, exist_ok=True)
        for existing in ("receipt.json", TIMING_RECEIPT):
            if (self.out / existing).exists():
                raise StartupError(f"{self.out / existing} exists; a rerun needs a new run root")
        prepare_runtime(self.out, args.device)  # before anything imports torch
        self.guard.install()
        started = time.perf_counter()
        bundle, self.lane, self.hashes, source, lane_codec = startup_checks(args)
        self.timings["process_to_startup"] = started - PROCESS_STARTED
        self.timings["startup"] = time.perf_counter() - started
        started = time.perf_counter()
        artifact = dhd.derive_dev_artifact(bundle, source, lane_codec, self.lane)
        del bundle
        artifact_bytes = dhd.canonical_artifact_bytes(artifact)
        artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()
        pinned = self.ckpt / "dev-artifact.sha256"
        if pinned.is_file() and pinned.read_text(encoding="utf-8").strip() != artifact_sha:
            raise dhd.DenseDataError("the continuation derived a different development artifact")
        (self.out / "dev-artifact.json").write_bytes(artifact_bytes)
        pinned.parent.mkdir(parents=True, exist_ok=True)
        pinned.write_text(artifact_sha + "\n", encoding="utf-8")
        self.hashes["dev_artifact_sha256"] = artifact_sha
        self.timings["derive"] = time.perf_counter() - started
        self.guard.poll("after-derive")
        if args.profile == "timing":
            return self.timing_run(artifact, lane_codec)
        return self.evaluate_and_read(artifact, lane_codec)

    # ------------------------------------------------------------------ lanes

    def load(self) -> tuple[Any, Any, list[int], bool, str, float, Any]:
        import torch

        from harness import dense_headroom_torch_v2 as dht2
        from harness import sparse_indexer_torch as sit

        lane = self.lane
        sit.set_determinism(allow_tf32=True)
        device = torch.device("cuda:0" if self.args.device == "cuda" else "cpu")
        started = time.perf_counter()
        model = sit.load_teacher(self.args.model_dir, device)
        config = model.config
        layers = dht2.attention_layers(config)
        if (int(config.num_hidden_layers) != lane.n_layers
                or tuple(layers) != lane.attention_layers):
            raise StartupError(f"model has layers {layers} of {config.num_hidden_layers}; the "
                               f"lane registers {lane.attention_layers} of {lane.n_layers}")
        hybrid = dht2.is_hybrid(config)
        determinism = "strict"
        if hybrid:
            # The gated-delta layers' kernels are outside torch's deterministic
            # registry; keep deterministic torch kernels, but warn instead of
            # raising on an op that has none (v1's decision 9, unchanged).
            torch.use_deterministic_algorithms(True, warn_only=True)
            determinism = "warn_only"
        self.timings["model_load"] = time.perf_counter() - started
        self.guard.poll("after-model-load")
        return model, device, layers, hybrid, determinism, dht2.scaling_of(config), dht2

    def unit_inputs(self, view: Any, unit: Any, content: Any) -> dict[str, Any]:
        tokens, q0, q1, n0, n1 = view.unit_tokens(unit.context_index, unit.query_index)
        context = view.contexts[unit.context_index]
        options, option_bytes, answer = ([], [], -1)
        if unit.mc:
            options, option_bytes, answer = view.options(unit.query_index)
        languages = (context["needle_language"], view.queries[unit.query_index]["language"])
        lex = (dhd.lexical_block_scores(tokens, int(context["length"]), q0, q1, languages,
                                        content) if unit.select else None)
        return {"tokens": tokens, "q0": q0, "q1": q1, "n0": n0, "n1": n1,
                "k_blocks": dhd.budget_blocks(int(context["length"])),
                "options": options, "option_bytes": option_bytes, "answer": answer, "lex": lex}

    def evaluate(self, dht_module: Any, model: Any, unit: Any, inputs: dict[str, Any],
                 layers: list[int], scaling: float, names: list[str], hybrid: bool,
                 device: Any, timer: Any = None) -> Any:
        kwargs = {"timer": timer} if timer is not None else {}
        return dht_module.evaluate_unit(
            model, inputs["tokens"], inputs["q0"], inputs["q1"], inputs["n0"], inputs["n1"],
            layers=layers, k_blocks=inputs["k_blocks"],
            fixed_k_blocks=dhd.fixed_blocks(self.lane.profile), scaling=scaling,
            do_select=unit.select, do_mc=unit.mc, options=inputs["options"],
            option_bytes=inputs["option_bytes"], answer=inputs["answer"],
            lex_blocks=inputs["lex"], seeds=self.args.seeds, unit_key=unit.unit_id,
            names=names, hybrid=hybrid, device=device, **kwargs)

    def evaluate_and_read(self, artifact: dict[str, Any], lane_codec: Any) -> int:
        import torch

        from harness import sparse_indexer_k1_marker as marker

        args, lane = self.args, self.lane
        view = dhd.DevView(artifact)
        units = dhd.plan_units(view.prompts)
        names = dhs.selector_names(args.seeds)
        model, device, layers, hybrid, determinism, scaling, dht2 = self.load()
        content = dhd.ContentFilter(lane_codec, artifact["stop_ids"])
        eval_dir = self.ckpt / "eval"
        chunk_seconds: dict[str, list[float]] = {}
        for stage in dhd.STAGES:
            stage_units = [u for u in units if u.stage == stage]
            started = time.perf_counter()
            evaluated = 0
            for start in range(0, len(stage_units), CHUNK_UNITS):
                chunk = stage_units[start : start + CHUNK_UNITS]
                ids = [u.unit_id for u in chunk]
                path = eval_dir / stage / f"chunk-{chunk_name(ids)}.npz"
                if path.exists():
                    continue
                if self.guard.poll(f"{stage}:{start // CHUNK_UNITS}"):
                    self.interrupt(units, eval_dir, names, marker)
                chunk_started = time.perf_counter()
                records = []
                for unit in chunk:
                    output = self.evaluate(dht2, model, unit, self.unit_inputs(view, unit,
                                                                               content),
                                           layers, scaling, names, hybrid, device)
                    records.append(dict(dht2.unit_record(output)))
                    self.guard.poll()
                evaluated += len(chunk)
                save_chunk(path, ids, records, names)
                chunk_seconds.setdefault(stage, []).append(time.perf_counter() - chunk_started)
            self.timings[f"eval:{stage}"] = time.perf_counter() - started
            self.timings[f"eval:{stage}:units_evaluated"] = float(evaluated)
        self.timings["chunk_seconds"] = chunk_seconds
        k_limits = {unit.unit_id: (max(dhd.budget_blocks(int(view.contexts[unit.context_index][
            "length"])), dhd.fixed_blocks(lane.profile)) * dhd.BLOCK_SIZE + 3) for unit in units}
        results = collect(eval_dir, names)
        coverage = dhs.check_coverage(units, results, k_limits)
        started = time.perf_counter()
        replicates = dhs.REPLICATES if lane.profile == "registered" else TINY_REPLICATES
        report = dhs.analyse(artifact, results, seeds=args.seeds, replicates=replicates,
                             reproduce_smoke=lane.lane_id == "qwen3-0.6b-base")
        self.timings["statistics"] = time.perf_counter() - started
        import transformers

        self.receipt("receipt.json", {
            "status": "PRECHECK_COMPLETE",
            "verdict_is_final": True,
            "decisions": report["decisions"],
            "report": report,
            "coverage": coverage,
            "artifact_counts": artifact["counts"],
            "attention_layers": layers,
            "hybrid": hybrid,
            "determinism": determinism,
            "selectors": names,
            "versions": {"torch": torch.__version__, "transformers": transformers.__version__,
                         "device": (torch.cuda.get_device_name(0) if device.type == "cuda"
                                    else "cpu")},
        })
        return EXIT_OK

    def interrupt(self, units: list[dhd.Unit], eval_dir: Path, names: list[str],
                  marker: Any) -> None:
        done = sum(1 for _ in eval_dir.glob("*/chunk-*.npz"))
        self.receipt("receipt-interrupted.json", {
            "status": "INTERRUPTED", "signal": self.guard.received, "chunks_on_disk": done,
            "units_planned": len(units), "resume_subpath": f"{OUTPUT_SUBDIR}/checkpoints"})
        marker.write_checkpoint_marker(self.marker, str(self.guard.received),
                                       f"{int(time.time())}-{os.getpid()}",
                                       {"chunks_on_disk": done})
        raise Interrupted()

    # ---------------------------------------------------------- timing job

    def timing_run(self, artifact: dict[str, Any], lane_codec: Any) -> int:
        """The development timing job (D36): see the module docstring."""

        import torch

        from harness import dense_headroom_torch as dht1
        from harness import sparse_indexer_k1_marker as marker

        args = self.args
        view = dhd.DevView(artifact)
        units = dhd.plan_units(view.prompts)
        names = dhs.selector_names(args.seeds)
        model, device, layers, hybrid, determinism, scaling, dht2 = self.load()
        content = dhd.ContentFilter(lane_codec, artifact["stop_ids"])
        subset, rest = dv2.timing_order(units, dhd.STAGES)
        report: dict[str, Any] = {
            "status": "TIMING_RUNNING", "determinism": determinism, "hybrid": hybrid,
            "attention_layers": layers, "artifact_counts": artifact["counts"],
            "dev_artifact_matches_v1_job_730": (self.hashes["dev_artifact_sha256"]
                                                == dv2.V1_LARGE_LANE_ARTIFACT_SHA256),
            "subset": [{"stage": s, "chunk": i, "units": [u.unit_id for u in c]}
                       for s, i, c in subset],
            "chunks": [], "units": [], "reference": [], "profiles": {}, "torch_profiles": {},
            "evaluation_started_after_s": time.perf_counter() - PROCESS_STARTED,
            "versions": {"torch": torch.__version__,
                         "device": (torch.cuda.get_device_name(0) if device.type == "cuda"
                                    else "cpu")},
        }
        outputs: dict[str, Any] = {}

        def finish(status: str) -> None:
            report["status"] = status
            report["process_seconds"] = time.perf_counter() - PROCESS_STARTED
            self.receipt(TIMING_RECEIPT, {"timing": report})

        def run_chunk(stage: str, index: int, chunk: list[Any], phase: str,
                      profile: bool) -> None:
            if self.guard.poll(f"{phase}:{stage}:{index}"):
                raise Interrupted()
            profiler = cProfile.Profile() if profile else None
            ticks = thread_ticks()
            started = time.perf_counter()
            cpu = time.process_time()
            if profiler is not None:
                profiler.enable()
            for unit in chunk:
                inputs = self.unit_inputs(view, unit, content)
                timer = dht2.UnitTimer(device)
                unit_started = time.perf_counter()
                output = self.evaluate(dht2, model, unit, inputs, layers, scaling, names,
                                       hybrid, device, timer)
                outputs[unit.unit_id] = dict(dht2.unit_record(output))
                report["units"].append({
                    "unit": unit.unit_id, "stage": stage, "chunk": index, "phase": phase,
                    "seconds": time.perf_counter() - unit_started,
                    "context_tokens": int(len(inputs["tokens"])),
                    "select": bool(unit.select), "mc": bool(unit.mc),
                    "options": len(inputs["options"]), "parts": timer.as_dict()})
                self.guard.poll()
            if profiler is not None:
                profiler.disable()
                text = io.StringIO()
                stats = pstats.Stats(profiler, stream=text)
                stats.sort_stats("tottime").print_stats(30)
                stats.sort_stats("cumulative").print_stats(40)
                report["profiles"][f"{phase}:{stage}:{index}"] = text.getvalue()[-30000:]
            report["chunks"].append({"stage": stage, "chunk": index, "phase": phase,
                                     "units": len(chunk), "profiled": profile,
                                     "seconds": time.perf_counter() - started,
                                     "cpu_seconds": time.process_time() - cpu,
                                     "busiest_threads": busiest_threads(ticks, thread_ticks())})
            dhd.write_json(self.out / "timing-progress.json", _jsonable({
                "chunks": len(report["chunks"]), "units": len(report["units"]),
                "last": [stage, index, phase],
                "subset_complete": bool(report.get("subset_complete")),
                "seconds": time.perf_counter() - PROCESS_STARTED}))

        def reference(unit: Any, tag: str) -> None:
            """v1's path on a unit v2 already evaluated: timed, profiled, compared bit for bit."""

            if self.guard.poll(f"reference:{tag}"):
                raise Interrupted()
            inputs = self.unit_inputs(view, unit, content)
            profiler = cProfile.Profile()
            started = time.perf_counter()
            profiler.enable()
            old = dict(dht1.unit_record(self.evaluate(dht1, model, unit, inputs, layers, scaling,
                                                      names, hybrid, device)))
            profiler.disable()
            seconds = time.perf_counter() - started
            text = io.StringIO()
            stats = pstats.Stats(profiler, stream=text)
            stats.sort_stats("tottime").print_stats(30)
            stats.sort_stats("cumulative").print_stats(40)
            report["profiles"][f"v1-reference:{unit.unit_id}"] = text.getvalue()[-30000:]
            equal = _records_equal(old, outputs[unit.unit_id])
            report["reference"].append({"unit": unit.unit_id, "stage": unit.stage,
                                        "v1_seconds": seconds, "bitwise_equal": equal})

        try:
            # 1. The first subset chunk (A-main 0; its first unit pays the kernel compiles).
            stage, index, chunk = subset[0]
            run_chunk(stage, index, chunk, "subset", profile=False)
            # 2. Diagnostics early, so that a job still CPU-bound records why before the
            #    signal: torch.profiler on one warm unit through each path, then v1's path
            #    on the chunk's first two units, compared bit for bit with v2's.
            warm = chunk[1] if len(chunk) > 1 else chunk[0]
            warm_inputs = self.unit_inputs(view, warm, content)
            for label, module in (("v2", dht2), ("v1", dht1)):
                if self.guard.poll(f"torch-profile:{label}"):
                    raise Interrupted()
                report["torch_profiles"][label] = torch_profile(
                    lambda module=module: self.evaluate(module, model, warm, warm_inputs,
                                                        layers, scaling, names, hybrid, device),
                    device)
            for unit in chunk[:2]:
                reference(unit, "A")
            # 3. The rest of the registered subset.
            for stage, index, chunk in subset[1:]:
                run_chunk(stage, index, chunk, "subset", profile=False)
            report["subset_complete"] = True
            report["subset_finished_after_s"] = time.perf_counter() - PROCESS_STARTED
            dhd.write_json(self.out / "timing-progress.json", _jsonable({
                "chunks": len(report["chunks"]), "units": len(report["units"]),
                "subset_complete": True, "seconds": report["subset_finished_after_s"]}))
            # 4. v1's path on the first unit of every other stage.
            for stage, index, chunk in subset[1:]:
                if index == 0:
                    for unit in chunk[:TIMING_REFERENCE_UNITS_PER_STAGE]:
                        reference(unit, stage)
            # 5. The lane's other chunks until a signal (the live test of the signal path).
            profiled: set[str] = set()
            for stage, index, chunk in rest:
                run_chunk(stage, index, chunk, "continue", profile=stage not in profiled)
                profiled.add(stage)
        except Interrupted:
            finish("TIMING_INTERRUPTED")
            marker.write_checkpoint_marker(self.marker, str(self.guard.received),
                                           f"{int(time.time())}-{os.getpid()}",
                                           {"timing_units": len(report["units"])})
            raise
        finish("TIMING_COMPLETE")
        return EXIT_OK


def thread_ticks() -> dict[str, tuple[str, int]]:
    """CPU clock ticks (user + system) of every thread of this process (Linux)."""

    out: dict[str, tuple[str, int]] = {}
    task = Path("/proc/self/task")
    if not task.is_dir():
        return out
    for entry in task.iterdir():
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            name = (entry / "comm").read_text().strip()
        except (OSError, IndexError):
            continue
        out[entry.name] = (name, int(fields[11]) + int(fields[12]))
    return out


def busiest_threads(before: dict[str, tuple[str, int]], after: dict[str, tuple[str, int]],
                    top: int = 5) -> list[dict[str, Any]]:
    deltas = [{"tid": tid, "name": name, "ticks": ticks - before.get(tid, (name, 0))[1]}
              for tid, (name, ticks) in after.items()]
    return sorted(deltas, key=lambda d: -d["ticks"])[:top]


def torch_profile(fn: Any, device: Any) -> dict[str, Any]:
    """One call under torch.profiler: the top operators by self CPU time and by
    device time (development diagnostics only; failures are recorded)."""

    import torch

    activities = [torch.profiler.ProfilerActivity.CPU]
    if device.type == "cuda":
        activities.append(torch.profiler.ProfilerActivity.CUDA)
    try:
        with torch.profiler.profile(activities=activities) as profiler:
            fn()
        averages = profiler.key_averages()
        by_cpu = averages.table(sort_by="self_cpu_time_total", row_limit=30)
        by_device = (averages.table(sort_by="self_device_time_total", row_limit=20)
                     if device.type == "cuda" else "")
        return {"status": "ok", "by_self_cpu": by_cpu[-20000:], "by_device": by_device[-15000:]}
    except Exception as exc:  # noqa: BLE001 - a diagnostic must not end the timing job
        return {"status": f"failed: {type(exc).__name__}: {exc}"[:500]}


def _records_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if set(a) != set(b):
        return False
    for key in a:
        x, y = np.asarray(a[key]), np.asarray(b[key])
        if x.shape != y.shape or x.dtype != y.dtype:
            return False
        if x.dtype.kind == "f":
            if not np.array_equal(x.view(np.uint8), y.view(np.uint8)):
                return False
        elif not np.array_equal(x, y):
            return False
    return True


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (set, frozenset)):
        return sorted(_jsonable(v) for v in value)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    job = Job(args)
    try:
        return job.run()
    except StartupError as exc:
        print(f"CONTRACT: {exc}", file=sys.stderr)
        return EXIT_CONTRACT
    except Interrupted:
        print("INTERRUPTED: completed chunks saved; marker written; exit 75", file=sys.stderr)
        return EXIT_CHECKPOINTED
    except Exception:  # noqa: BLE001 - every other failure is an integrity failure
        traceback.print_exc()
        return EXIT_INTEGRITY


if __name__ == "__main__":
    raise SystemExit(main())
