#!/usr/bin/env python3
"""GPU entry point of the Q3 dense headroom pre-check (q3-dense-headroom-precheck-v1).

One lane per job: a frozen base (Qwen3-0.6B-Base or Qwen3.5-4B-Base) reads the
development partition of the K1 bundle, densely, with no indexer. The job

1. verifies the bundle, the frozen preregistration (and its ledger row), the
   model receipt and, in the registered profile, that every code file it runs
   has the SHA-256 the preregistration tables (exit 2 otherwise);
2. derives the development artifact (``harness/dense_headroom_data.py``):
   development prompts only, the development literal prompts, re-tokenized
   for a base whose tokenizer differs from the bundle's, and the model-free
   text features; its SHA-256 goes in the receipt;
3. evaluates every unit in the registered stage order (main MN/CX, needle
   absent, literal, no haystack), one atomic chunk file per 16 units;
4. computes the registered statistics and lane decisions
   (``harness/dense_headroom_stats.py``) and writes ``receipt.json``.

The process is PID 1 in its container. SIGUSR1 or SIGTERM is honoured between
chunks: completed chunks are already on disk, ``receipt-interrupted.json`` is
written, then the checkpoint marker (``trigger=SIG<name>``), and the job exits
75. A continuation in the same run root (``resume_subpath``
``dense-precheck/checkpoints``) skips completed chunks and refuses a different
development artifact. Exit codes: 0 complete, 2 startup contract, 3 integrity,
75 interrupted after a confirmed save.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402

from harness import dense_headroom_data as dhd  # noqa: E402
from harness import dense_headroom_stats as dhs  # noqa: E402

EXIT_OK = 0
EXIT_CONTRACT = 2
EXIT_INTEGRITY = 3
EXIT_CHECKPOINTED = 75
CHUNK_UNITS = 16
TINY_REPLICATES = 200
OUTPUT_SUBDIR = "dense-precheck"
CODE_FILES = (
    "scripts/run_dense_headroom_precheck.py",
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
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--expected-preregistration-sha256", required=True)
    parser.add_argument("--experiment-id", default=dhd.EXPERIMENT_ID)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--ledger-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--profile", choices=("registered", "tiny"), default="registered")
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
        raise StartupError("the registered profile needs --source-tokenizer")
    source = dhd.ByteLevelCodec(args.source_tokenizer)
    lane_codec = dhd.ByteLevelCodec(args.model_dir / "tokenizer.json")
    return source, lane_codec


def startup_checks(args: argparse.Namespace) -> tuple[dict[str, Any], dhd.Lane, dict[str, Any],
                                                      Any, Any]:
    """Fail closed before any work; returns (bundle, lane, hashes, source, lane codec)."""

    from harness import sparse_indexer_data as sid
    from scripts import preregister

    if args.experiment_id != dhd.EXPERIMENT_ID:
        raise StartupError(f"experiment id must be {dhd.EXPERIMENT_ID}")
    if args.seeds != list(dhd.SEEDS):
        raise StartupError(f"seeds must be {list(dhd.SEEDS)}")
    try:
        lane = dhd.lane_of(args.lane)
    except dhd.DenseDataError as exc:
        raise StartupError(str(exc)) from exc
    if lane.profile != args.profile:
        raise StartupError(f"lane {lane.lane_id} belongs to the {lane.profile} profile")
    if lane.profile == "registered" and args.expected_evidence_sha256 != dhd.SOURCE_BUNDLE_SHA256:
        raise StartupError("the registered profile reads only the K1 bundle 919d016b...")
    try:
        bundle = sid.load_bundle(args.evidence, args.expected_evidence_sha256)
    except (OSError, sid.DataContractError) as exc:
        raise StartupError(f"bundle check failed: {exc}") from exc
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
    code = code_hashes()
    if lane.profile == "registered":
        table = tabled_code(args.preregistration.read_text(encoding="utf-8"))
        differing = sorted(name for name in CODE_FILES if table.get(name) != code[name])
        if differing:
            raise StartupError(f"code differs from the preregistration's table: {differing}")
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
    if lane.profile == "registered":
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
    output_root = os.environ.get("COTCODEC_OUTPUT_DIR")
    if output_root:
        manifest_path = Path(output_root) / "manifest.json"
        if not manifest_path.is_file():
            raise StartupError("the batch manifest is missing from the output root")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("seeds") != args.seeds:
            raise StartupError("manifest seeds differ from argv seeds")
        if manifest.get("model", {}).get("receipt_sha256") != receipt_sha:
            raise StartupError("manifest receipt digest differs")
        if manifest.get("study_artifact", {}).get("sha256") != args.expected_evidence_sha256:
            raise StartupError("manifest study artifact digest differs")
        if lane.profile == "registered" and (manifest.get("gpus") != lane.gpus
                                             or manifest.get("minutes") != lane.minutes):
            raise StartupError("manifest GPUs or minutes differ from the registered lane")
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
        "ledger_row_hash": str(row["hash"]),
        "receipt_sha256": receipt_sha,
        "source_tokenizer_sha256": source.sha256,
        "lane_tokenizer_sha256": lane_codec.sha256,
        "git_sha": os.environ.get("COTCODEC_GIT_SHA", "unknown"),
        "source_sha256": os.environ.get("COTCODEC_SOURCE_SHA256", "unknown"),
        "code": code,
    }
    return bundle, lane, hashes, source, lane_codec


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
        self.timings: dict[str, float] = {}
        self.hashes: dict[str, Any] = {}

    def receipt(self, name: str, payload: dict[str, Any]) -> str:
        payload = {**payload, "experiment_id": self.args.experiment_id,
                   "lane": self.lane.as_dict(), "profile": self.args.profile,
                   "seeds": list(self.args.seeds), "hashes": self.hashes,
                   "timings_s": self.timings,
                   "slurm_job_id": os.environ.get("SLURM_JOB_ID")}
        return dhd.write_json(self.out / name, _jsonable(payload))

    def run(self) -> int:
        args = self.args
        self.out.mkdir(parents=True, exist_ok=True)
        if (self.out / "receipt.json").exists():
            raise StartupError(f"{self.out / 'receipt.json'} exists; a rerun needs a new run root")
        prepare_runtime(self.out, args.device)  # before anything imports torch
        from harness import sparse_indexer_k1_runtime as rt

        self.flag = rt.SignalFlag()
        self.flag.install()
        started = time.perf_counter()
        bundle, self.lane, self.hashes, source, lane_codec = startup_checks(args)
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
        return self.evaluate_and_read(artifact, lane_codec)

    def evaluate_and_read(self, artifact: dict[str, Any], lane_codec: Any) -> int:
        import torch

        from harness import dense_headroom_torch as dht
        from harness import sparse_indexer_k1_marker as marker
        from harness import sparse_indexer_torch as sit

        args, lane = self.args, self.lane
        view = dhd.DevView(artifact)
        units = dhd.plan_units(view.prompts)
        names = dhs.selector_names(args.seeds)
        sit.set_determinism(allow_tf32=True)
        device = torch.device("cuda:0" if args.device == "cuda" else "cpu")
        started = time.perf_counter()
        model = sit.load_teacher(args.model_dir, device)
        config = model.config
        layers = dht.attention_layers(config)
        if (int(config.num_hidden_layers) != lane.n_layers
                or tuple(layers) != lane.attention_layers):
            raise StartupError(f"model has layers {layers} of {config.num_hidden_layers}; the "
                               f"lane registers {lane.attention_layers} of {lane.n_layers}")
        hybrid = dht.is_hybrid(config)
        determinism = "strict"
        if hybrid:
            # The gated-delta layers' kernels are outside torch's deterministic
            # registry; keep deterministic torch kernels, but warn instead of
            # raising on an op that has none (registered, decision 9).
            torch.use_deterministic_algorithms(True, warn_only=True)
            determinism = "warn_only"
        scaling = dht.scaling_of(config)
        self.timings["model_load"] = time.perf_counter() - started
        content = dhd.ContentFilter(lane_codec, artifact["stop_ids"])
        eval_dir = self.ckpt / "eval"
        k_limits: dict[str, int] = {}
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
                if self.flag.received:
                    self.interrupt(units, eval_dir, names, marker)
                records = []
                for unit in chunk:
                    tokens, q0, q1, n0, n1 = view.unit_tokens(unit.context_index,
                                                              unit.query_index)
                    context = view.contexts[unit.context_index]
                    k_blocks = dhd.budget_blocks(int(context["length"]))
                    options, option_bytes, answer = ([], [], -1)
                    if unit.mc:
                        options, option_bytes, answer = view.options(unit.query_index)
                    lex = (dhd.lexical_block_scores(tokens, int(context["length"]), q0, q1,
                                                    context["needle_language"], content)
                           if unit.select else None)
                    output = dht.evaluate_unit(
                        model, tokens, q0, q1, n0, n1, layers=layers, k_blocks=k_blocks,
                        fixed_k_blocks=dhd.fixed_blocks(lane.profile), scaling=scaling,
                        do_select=unit.select, do_mc=unit.mc, options=options,
                        option_bytes=option_bytes, answer=answer, lex_blocks=lex,
                        seeds=args.seeds, unit_key=unit.unit_id, names=names, hybrid=hybrid,
                        device=device)
                    records.append(dict(dht.unit_record(output)))
                evaluated += len(chunk)
                save_chunk(path, ids, records, names)
            self.timings[f"eval:{stage}"] = time.perf_counter() - started
            self.timings[f"eval:{stage}:units_evaluated"] = float(evaluated)
        for unit in units:
            context = view.contexts[unit.context_index]
            k_limits[unit.unit_id] = (max(dhd.budget_blocks(int(context["length"])),
                                          dhd.fixed_blocks(lane.profile)) * dhd.BLOCK_SIZE + 3)
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
            "status": "INTERRUPTED", "signal": self.flag.received, "chunks_on_disk": done,
            "units_planned": len(units), "resume_subpath": f"{OUTPUT_SUBDIR}/checkpoints"})
        marker.write_checkpoint_marker(self.marker, str(self.flag.received),
                                       f"{int(time.time())}-{os.getpid()}",
                                       {"chunks_on_disk": done})
        raise Interrupted()


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
