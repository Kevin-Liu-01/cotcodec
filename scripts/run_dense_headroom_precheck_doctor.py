#!/usr/bin/env python3
"""CPU doctor for the Q3 dense headroom pre-check on tiny random models.

Exercises every pre-check object before any GPU job: the byte-exact codecs and
the tail rule, the development artifact (identity lane and re-tokenized lane,
determinism, the needle span after re-tokenization, the development literal
prompts, the partition guard on prompts, contexts and queries), the text
features, the selectors against brute force and K1 v1's per-call functions,
the block-score null's seeding, multiple choice with a cropped attention cache
and a copied hybrid cache against a no-cache forward, the statistics and lane
decisions on hand-made tables, and the GPU entry point end to end on CPU for a
tiny Qwen3 (attention-only) and a tiny Qwen3.5-style hybrid (gated delta plus
full attention), each under the batch environment (``COTCODEC_OUTPUT_DIR``
with the job's ``manifest.json``): a digest mismatch exits 2, wrong seeds exit
2, SIGUSR1 after the first chunk exits 75 with the marker, a continuation from
the saved chunks (its manifest naming the predecessor and the resume subpath,
with the batch script's resume receipt) completes with the uninterrupted run's
numbers, the same continuation without its resume receipt exits 2, and a
continuation that derives a different artifact exits 3.

Every number is a synthetic-case number. A PASS proves executability and gate
semantics only; it says nothing about Qwen3-0.6B-Base, Qwen3.5-4B-Base, the
data or any K1 claim.
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import dense_headroom_data as dhd  # noqa: E402
from harness import dense_headroom_stats as dhs  # noqa: E402
from harness import sparse_indexer_data as sid  # noqa: E402

DOCTOR_NAME = "q3-dense-headroom-precheck-cpu-doctor"
EVIDENCE_GRADE = (
    "EXECUTABILITY_AND_GATE_SEMANTICS_ONLY: tiny randomly initialised Qwen3 and Qwen3.5-style "
    "models, stand-in byte and pair tokenizers and a synthetic K1 bundle built by the real K1 "
    "builder. Nothing here touches Qwen3-0.6B-Base, Qwen3.5-4B-Base, Belebele or FineWeb."
)
ENTRY = PROJECT_ROOT / "scripts" / "run_dense_headroom_precheck.py"
TINY_LAYERS = 4
HYBRID_VOCAB = 1024
ANCHOR_NAMES = ("Alice", "Bogota", "Kyoto", "Nairobi")


# --------------------------------------------------------------------------- #
# Fixtures shared with the tests
# --------------------------------------------------------------------------- #


def anchored_sources(seed: int = 7, links: int = 24) -> Any:
    """K1's synthetic sources with entity anchors in a share of the English rows."""

    from scripts.run_sparse_indexer_k1_doctor import synthetic_sources

    sources = synthetic_sources(seed=seed, links=links)
    rows = []
    for index, row in enumerate(sources.belebele["en"]):
        if index % 3 == 0:
            name = ANCHOR_NAMES[index % len(ANCHOR_NAMES)]
            year = 1900 + index
            row = dataclasses.replace(
                row, passage=f"{row.passage} {name} arrived in {year}.",
                question=f"en when did {name} arrive in {year}?")
        rows.append(row)
    sources.belebele["en"] = rows
    return sources


def tiny_params() -> Any:
    from scripts.run_sparse_indexer_k1_doctor import tiny_params as k1_tiny

    return dataclasses.replace(k1_tiny(), dev_families_per_pair=6)


def build_tiny_bundle(directory: Path) -> tuple[Path, str]:
    from scripts.build_sparse_indexer_k1_bundle import assemble_bundle, write_bundle
    from scripts.run_sparse_indexer_k1_doctor import ByteTokenizer

    bundle = assemble_bundle(anchored_sources(), ByteTokenizer(), tiny_params())
    path = directory / "k1-bundle-tiny.json"
    summary = write_bundle(bundle, path, tiny_params().max_bytes)
    return path, summary["sha256"]


def make_tiny_attention(directory: Path, seed: int = 0) -> Path:
    from scripts.run_sparse_indexer_k1_doctor import make_tiny_model

    return make_tiny_model(directory, seed=seed, layers=TINY_LAYERS)


def make_tiny_hybrid(directory: Path, seed: int = 0) -> Path:
    """A tiny Qwen3.5 checkpoint saved as the conditional-generation class (as the
    real Qwen3.5-4B-Base is): gated delta layers 0 and 2, full attention 1 and 3."""

    # CPU only: flash-linear-attention's Triton kernels cannot run here, so they
    # are blocked before transformers binds them (the entry point does the same).
    dhd.block_gpu_only_kernels()
    import torch
    from transformers import Qwen3_5Config, Qwen3_5ForConditionalGeneration

    torch.manual_seed(seed)
    text = {
        "vocab_size": HYBRID_VOCAB, "hidden_size": 64, "intermediate_size": 128,
        "num_hidden_layers": TINY_LAYERS, "num_attention_heads": 4, "num_key_value_heads": 2,
        "head_dim": 32, "linear_conv_kernel_dim": 4, "linear_key_head_dim": 16,
        "linear_num_key_heads": 2, "linear_num_value_heads": 4, "linear_value_head_dim": 16,
        "layer_types": ["linear_attention", "full_attention", "linear_attention",
                        "full_attention"],
        "max_position_embeddings": 4096, "tie_word_embeddings": True, "eos_token_id": 2,
        "rope_parameters": {"rope_type": "default", "rope_theta": 1e7,
                            "partial_rotary_factor": 0.25, "mrope_interleaved": True,
                            "mrope_section": [1, 1, 2]},
    }
    vision = {"depth": 1, "hidden_size": 32, "intermediate_size": 64, "num_heads": 2,
              "out_hidden_size": 64, "patch_size": 16, "spatial_merge_size": 2,
              "temporal_patch_size": 2, "num_position_embeddings": 64}
    model = Qwen3_5ForConditionalGeneration(Qwen3_5Config(text_config=text, vision_config=vision,
                                                           tie_word_embeddings=True))
    directory.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(directory, safe_serialization=True)
    return directory


def freeze_stand_in_prereg(root: Path) -> tuple[Path, str, Path]:
    from scripts import preregister

    prereg = root / "program" / "preregistrations" / f"{dhd.EXPERIMENT_ID}.md"
    prereg.parent.mkdir(parents=True, exist_ok=True)
    prereg.write_text("# doctor stand-in preregistration\n\nSynthetic only.\n",
                      encoding="utf-8")
    ledger = root / "program" / "preregistrations" / "ledger.jsonl"
    preregister.freeze(prereg, dhd.EXPERIMENT_ID, ledger=ledger, root=root)
    return prereg, preregister.sha256_file(prereg), ledger


def write_stand_in_receipt(path: Path, lane: dhd.Lane) -> str:
    payload = {"model_id": lane.model_id, "revision": lane.revision, "files": [],
               "note": "doctor stand-in; the real receipt is hashed in the job"}
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tiny_codecs(lane_id: str) -> tuple[Any, Any]:
    source = dhd.StandInByteCodec()
    return source, (dhd.StandInPairCodec() if dhd.lane_of(lane_id).retokenize else source)


class TinyRun:
    """Everything a CPU entry-point run needs for both tiny lanes."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.bundle, self.bundle_sha = build_tiny_bundle(root)
        self.models = {"tiny-attention": make_tiny_attention(root / "model-attention"),
                       "tiny-hybrid": make_tiny_hybrid(root / "model-hybrid")}
        self.prereg, self.prereg_sha, self.ledger = freeze_stand_in_prereg(root / "repo")
        self.receipts = {}
        for lane_id in self.models:
            path = root / f"receipt-{lane_id}.json"
            self.receipts[lane_id] = (path, write_stand_in_receipt(path, dhd.lane_of(lane_id)))

    def batch_files(self, lane_id: str, run_dir: Path, *, predecessor: str | None = None,
                    resume_receipt: bool = True) -> None:
        """The batch script's ``manifest.json`` (and ``resume-receipt.json`` for a
        continuation) in the job's output root, as the submitter flattens them."""

        manifest: dict[str, Any] = {
            "name": f"doctor-{lane_id}", "seeds": [42, 43, 44], "gpus": 0, "minutes": 0,
            "model": {"receipt_sha256": self.receipts[lane_id][1]},
            "study_artifact": {"sha256": self.bundle_sha}}
        if predecessor is not None:
            manifest["resume_from_job_id"] = predecessor
            manifest["resume_subpath"] = dhd.RESUME_SUBPATH
            if resume_receipt:
                (run_dir / "resume-receipt.json").write_text(json.dumps(
                    {"schema_version": 1, "predecessor_job_id": predecessor,
                     "resume_subpath": dhd.RESUME_SUBPATH}) + "\n", encoding="utf-8")
        (run_dir / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n",
                                               encoding="utf-8")

    def argv(self, lane_id: str, run_dir: Path, *, bundle_sha: str | None = None,
             seeds: tuple[str, ...] = ("42", "43", "44")) -> list[str]:
        receipt, receipt_sha = self.receipts[lane_id]
        return [
            sys.executable, str(ENTRY), "--lane", lane_id,
            "--output-dir", str(run_dir / "dense-precheck"),
            "--evidence", str(self.bundle),
            "--expected-evidence-sha256", bundle_sha or self.bundle_sha,
            "--model-dir", str(self.models[lane_id]),
            "--receipt", str(receipt), "--expected-receipt-sha256", receipt_sha,
            "--preregistration", str(self.prereg),
            "--expected-preregistration-sha256", self.prereg_sha,
            "--ledger", str(self.ledger), "--ledger-root", str(self.root / "repo"),
            "--seeds", *seeds, "--profile", "tiny", "--device", "cpu",
        ]

    @staticmethod
    def env(run_dir: Path, batch: bool = True) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith("COTCODEC_")}
        env["COTCODEC_CHECKPOINT_MARKER"] = str(run_dir / "checkpoint.ready")
        if batch:
            env["COTCODEC_OUTPUT_DIR"] = str(run_dir)
        env["OMP_NUM_THREADS"] = "2"
        env["PYTHONHASHSEED"] = "0"
        env["HF_HUB_OFFLINE"] = "1"
        return env

    def run(self, lane_id: str, run_dir: Path, timeout: int = 1800, *,
            predecessor: str | None = None, resume_receipt: bool = True,
            **kwargs: Any) -> subprocess.CompletedProcess:
        run_dir.mkdir(parents=True, exist_ok=True)
        self.batch_files(lane_id, run_dir, predecessor=predecessor,
                         resume_receipt=resume_receipt)
        return subprocess.run(self.argv(lane_id, run_dir, **kwargs), env=self.env(run_dir),
                              capture_output=True, text=True, timeout=timeout, check=False)


def load_bundle(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def receipt_of(run_dir: Path, name: str = "receipt.json") -> dict[str, Any]:
    return json.loads((run_dir / "dense-precheck" / name).read_text(encoding="utf-8"))


def _check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


# --------------------------------------------------------------------------- #
# Cases
# --------------------------------------------------------------------------- #


def case_codecs() -> dict[str, Any]:
    failures: list[str] = []
    byte, pair = dhd.StandInByteCodec(), dhd.StandInPairCodec()
    for text in ("hello world", "naïve café", "日本語のテキスト", "ab\n\ncd"):
        for codec in (byte, pair):
            _check(codec.decode_bytes(codec.encode(text)).decode() == text,
                   f"{type(codec).__name__} does not round-trip {text!r}", failures)
    _check(len(pair.encode("abcdef")) == 3 and len(byte.encode("abcdef")) == 6,
           "the pair stand-in does not change lengths", failures)
    raw = "aé".encode()
    cut = byte.encode("aé")[:-1]  # the last byte of é removed
    _check(dhd.decode_text(byte, cut, tail_tolerant=True) == ("a", 1),
           "an incomplete tail is not dropped", failures)
    try:
        dhd.decode_text(byte, cut)
        failures.append("an incomplete tail outside the haystack tail was accepted")
    except dhd.DenseDataError:
        pass
    del raw
    try:
        from tokenizers import Tokenizer, models, pre_tokenizers

        tok = Tokenizer(models.BPE(vocab={c: i for i, c in enumerate(
            dhd._bytes_to_unicode().values())}, merges=[]))
        tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False)
        tok.add_special_tokens(["<|endoftext|>"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tokenizer.json"
            tok.save(str(path))
            codec = dhd.ByteLevelCodec(path)
            for text in ("Ελληνικά 1990", "বাংলা ১৯৯০", "x\n\ny"):
                _check(codec.decode_bytes(codec.encode(text)).decode() == text,
                       f"byte-level codec does not round-trip {text!r}", failures)
            try:
                codec.decode_bytes([codec.sink])
                failures.append("a special token inside a segment was accepted")
            except dhd.DenseDataError:
                pass
        byte_level = "checked"
    except ImportError:
        byte_level = "skipped (tokenizers not installed)"
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "byte_level_codec": byte_level}


def case_features() -> dict[str, Any]:
    failures: list[str] = []
    anchors = dhd.english_anchors(
        "When did Alice's team reach Kyoto in 1990?",
        "Alice and her team reached Kyoto on 3 May 1990 after a long trip.")
    _check(anchors == {"capitalised": ["Alice", "Kyoto"], "digits": ["1990"]},
           f"English anchors {anchors}", failures)
    plain = dhd.english_anchors("What did the author describe?", "The author described rain.")
    _check(plain == {"capitalised": [], "digits": []}, "a first word counted as an anchor",
           failures)
    _check(dhd.digit_runs("১৯৯০ and ٢٠٢٠ and 7") == {"1990", "2020", "7"},
           "digits of other scripts are not normalised", failures)
    codec = dhd.StandInByteCodec()
    _check(dhd.symbol_only(codec, codec.encode(" ")[0])
           and not dhd.symbol_only(codec, codec.encode("a")[0]),
           "symbol-only tokens misclassified", failures)
    _check(dhd.budget_blocks(8192) == 256 and dhd.budget_blocks(6000) == 187
           and dhd.budget_blocks(128) == 4, "the matched budget is wrong", failures)
    return {"status": "PASS" if not failures else "FAIL", "failures": failures}


def case_derive(tmp: Path) -> dict[str, Any]:
    failures: list[str] = []
    path, _ = build_tiny_bundle(tmp)
    bundle = load_bundle(path)
    out: dict[str, Any] = {}
    for lane_id in ("tiny-attention", "tiny-hybrid"):
        lane = dhd.lane_of(lane_id)
        source, codec = tiny_codecs(lane_id)
        artifact = dhd.derive_dev_artifact(bundle, source, codec, lane)
        again = dhd.derive_dev_artifact(load_bundle(path), source, codec, lane)
        _check(dhd.artifact_sha256(artifact) == dhd.artifact_sha256(again),
               f"{lane_id}: the artifact is not deterministic", failures)
        view = dhd.DevView(artifact)
        section = bundle["eval"]
        ctx = sid.decode_array(section["context_tokens"])
        off = sid.decode_array(section["context_offsets"])
        for index, meta in enumerate(view.contexts):
            src = ctx[off[meta["source_index"]] : off[meta["source_index"] + 1]]
            mine = view.context(index)
            if not lane.retokenize:
                _check(np.array_equal(src, mine), f"{lane_id}: context {index} changed",
                       failures)
            elif meta["kind"] != "absent":
                s_meta = section["context_meta"][meta["source_index"]]
                src_needle = source.decode_bytes(src[s_meta["needle_start"]:
                                                     s_meta["needle_end"]])
                lane_needle = codec.decode_bytes(mine[meta["needle_start"]:
                                                      meta["needle_end"]])
                _check(src_needle == lane_needle, f"{lane_id}: needle {index} moved", failures)
                _check(int(mine[0]) == codec.sink, f"{lane_id}: no lane sink", failures)
        roles = artifact["counts"]["prompts_by_role"]
        _check(set(roles) == {"dev", "dev-absent", "dev-nohaystack", "dev-literal"},
               f"{lane_id}: roles {roles}", failures)
        for prompt in view.prompts:
            if prompt["role"] != "dev-literal":
                continue
            tokens, q0, q1, n0, n1 = view.unit_tokens(prompt["context_index"],
                                                      prompt["query_index"])
            sentence = codec.decode_bytes(tokens[q0:q1])
            _check(sentence in codec.decode_bytes(tokens[n0:n1]),
                   f"{lane_id}: literal query is not verbatim", failures)
        units = dhd.plan_units(view.prompts)
        _check(len({u.unit_id for u in units}) == len(units), "duplicate units", failures)
        anchored = sum(f["anchored"] for f in artifact["features"]["questions"].values())
        out[lane_id] = {"sha256": dhd.artifact_sha256(artifact), "units": len(units),
                        "anchored_questions": anchored,
                        "questions": len(artifact["features"]["questions"]),
                        "context_length": artifact["counts"]["context_length"]}
    _check(0 < out["tiny-attention"]["anchored_questions"]
           < out["tiny-attention"]["questions"], "no anchored and unanchored mix", failures)
    _check(out["tiny-hybrid"]["context_length"] != out["tiny-attention"]["context_length"],
           "re-tokenization did not change lengths", failures)
    # Fail-closed partition reads.
    split = bundle["split"]
    for label, tamper in (
        ("prompt cluster", lambda b: b["eval"]["prompts"].__setitem__(
            _first_dev(b), {**b["eval"]["prompts"][_first_dev(b)],
                            "cluster": split["audit"][0]})),
        ("context partition", lambda b: b["eval"]["context_meta"][
            b["eval"]["prompts"][_first_dev(b)]["context_index"]].__setitem__(
                "partition", "audit")),
        ("query link", lambda b: b["eval"]["query_meta"][
            b["eval"]["prompts"][_first_dev(b)]["query_index"]].__setitem__(
                "link", split["audit"][0])),
    ):
        tampered = copy.deepcopy(bundle)
        tamper(tampered)
        try:
            dhd.derive_dev_artifact(tampered, *tiny_codecs("tiny-attention"),
                                    dhd.lane_of("tiny-attention"))
            failures.append(f"a {label} outside the development partition was accepted")
        except Exception as exc:  # noqa: BLE001 - any fail-closed error is the expected outcome
            out[f"refused_{label.replace(' ', '_')}"] = type(exc).__name__
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, **out}


def _first_dev(bundle: dict[str, Any]) -> int:
    return next(i for i, p in enumerate(bundle["eval"]["prompts"])
                if p["partition"] == "development" and p["role"] == "dev")


def case_selectors(tmp: Path) -> dict[str, Any]:
    import itertools

    import torch

    from harness import dense_headroom_torch as dht
    from harness import sparse_indexer_torch as sit

    failures: list[str] = []
    rng = np.random.default_rng(0)
    # Expected recall under random tie-breaking against enumeration.
    for _ in range(30):
        n_blocks, k = int(rng.integers(5, 9)), int(rng.integers(1, 5))
        scores = torch.as_tensor(rng.integers(0, 3, size=(1, n_blocks)).astype(np.float32))
        valid = torch.ones((1, n_blocks), dtype=torch.bool)
        cover = torch.as_tensor(rng.integers(0, 5, size=n_blocks))
        hits, _ = dht.expected_topk_hits(scores, valid, k, cover, torch.zeros(1))
        order = np.argsort(-scores[0].numpy(), kind="stable")
        kth = np.sort(scores[0].numpy())[::-1][k - 1]
        above = [b for b in order if scores[0, b] > kth]
        tie = [b for b in order if scores[0, b] == kth]
        picks = [sum(int(cover[b]) for b in above) + sum(int(cover[b]) for b in combo)
                 for combo in itertools.combinations(tie, k - len(above))]
        _check(abs(float(hits[0]) - float(np.mean(picks))) < 1e-9,
               "expected tie recall differs from enumeration", failures)
    # The matched selectors against K1 v1's per-call functions on a tiny model unit.
    model_dir = make_tiny_attention(tmp / "attention")
    model = sit.load_teacher(model_dir, "cpu", dtype=torch.float32)
    sit.set_determinism(allow_tf32=False)
    length, n0, n1 = 96, 30, 50
    tokens = rng.integers(2, 500, size=length).astype(np.int64)
    q0, q1 = 80, 92
    rows = torch.arange(q0, q1)
    names = dhs.selector_names([42, 43, 44])
    with sit.CaptureSession(model, range(TINY_LAYERS), query_rows=rows) as cap, \
            torch.no_grad():
        model(input_ids=torch.as_tensor(tokens)[None], use_cache=False)
        lex = torch.as_tensor(rng.integers(0, 3, size=length // 4).astype(np.float32))
        recall, _, selected, finite = dht.select_unit(
            cap, rows, q0, n0, n1, layers=list(range(TINY_LAYERS)), k_blocks=4,
            fixed_k_blocks=4, scaling=dht.scaling_of(model.config), lex_blocks=lex,
            seeds=[42, 43, 44], unit_key="u", names=names)
        for layer in range(TINY_LAYERS):
            probs = sit.head_probs_rows(cap.query[layer][0], cap.key[layer][0], rows,
                                        dht.scaling_of(model.config))
            dense = sit.block_targets(probs, rows, include_hm=True)
            for col, target in enumerate(("hs", "mp", "hm")):
                chosen = sit.select_top_blocks(dense[target], dense["valid"], 4)
                v1 = float(sit.block_selection_recall(chosen, rows, n0, n1).mean()) * 100
                _check(abs(v1 - float(recall[layer, col])) < 1e-4,
                       f"T:{target} differs from K1 v1 at layer {layer}", failures)
            u = float(sit.union_topk_recall(probs, rows, 16, n0, n1).mean()) * 100
            _check(abs(u - float(recall[layer, names.index("U")])) < 1e-4,
                   "U differs from K1 v1", failures)
            r = float(sit.random_block_recall(rows, n0, n1, 4).mean()) * 100
            _check(abs(r - float(recall[layer, names.index("rand")])) < 1e-4,
                   "rand differs from K1 v1", failures)
            _check(float(recall[layer, names.index("T:hs@fixed")])
                   == float(recall[layer, names.index("T:hs")]),
                   "fixed and matched budgets differ at equal k", failures)
    _check(bool(finite) and int(selected) <= 4 * 4 + 3, "selection budget or finiteness",
           failures)
    a = dht.null_noise(42, "u", 0, (3, 5), torch.device("cpu"))
    b = dht.null_noise(42, "u", 0, (3, 5), torch.device("cpu"))
    c = dht.null_noise(43, "u", 0, (3, 5), torch.device("cpu"))
    _check(torch.equal(a, b) and not torch.equal(a, c), "null noise seeding", failures)
    return {"status": "PASS" if not failures else "FAIL", "failures": failures}


def case_multiple_choice(tmp: Path) -> dict[str, Any]:
    import torch
    from transformers import DynamicCache

    from harness import dense_headroom_torch as dht
    from harness import sparse_indexer_torch as sit

    failures: list[str] = []
    rng = np.random.default_rng(1)
    gaps = {}
    for label, maker, vocab in (("attention", make_tiny_attention, 500),
                                ("hybrid", make_tiny_hybrid, HYBRID_VOCAB - 1)):
        model = sit.load_teacher(maker(tmp / label), "cpu", dtype=torch.float32)
        hybrid = dht.is_hybrid(model.config)
        prompt = torch.as_tensor(rng.integers(3, vocab, size=40))[None]
        options = [rng.integers(3, vocab, size=n) for n in (1, 3, 5, 2)]
        cache = DynamicCache(config=model.config)
        with torch.no_grad():
            out = model(input_ids=prompt, use_cache=True, past_key_values=cache,
                        logits_to_keep=1)
            cached = dht.option_scores(model, cache, out.logits[0, -1], options, [1, 1, 1, 1],
                                       prompt.shape[1], torch.device("cpu"), hybrid)
            worst = 0.0
            for option, score in zip(options, cached, strict=True):
                full = torch.cat([prompt[0], torch.as_tensor(option)])[None]
                logp = torch.log_softmax(model(input_ids=full).logits[0].float(), dim=-1)
                reference = sum(float(logp[prompt.shape[1] - 1 + i, int(t)])
                                for i, t in enumerate(option))
                worst = max(worst, abs(reference - score))
        gaps[label] = worst
        _check(worst < 1e-3, f"{label}: cached option scores differ by {worst}", failures)
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "max_abs_gap": gaps}


def _results_fixture(levels: dict[str, float], seeds: list[int]) -> tuple[dict, dhs.Results]:
    """A hand-made artifact and results: 6 questions in 6 clusters, pairs ja>en and en>ja,
    one unit per prompt; even questions carry entity anchors."""

    names = dhs.selector_names(seeds)
    prompts: list[dict[str, Any]] = []
    units: dict[str, Any] = {}
    contexts: list[dict[str, Any]] = []
    features: dict[str, Any] = {"questions": {}, "prompt_overlap": {},
                                "token_counts": {"passage": {}, "question": {}}}
    rng = np.random.default_rng(3)

    def add(prompt: dict[str, Any], cond: str, mc: bool) -> None:
        index = len(contexts)
        language = prompt["needle_language"]
        contexts.append({"kind": "needle", "needle_language": language, "length": 8192,
                         "needle_start": 100, "needle_end": 200 if language == "en" else 240,
                         "depth": 0.5})
        prompt.update(context_index=index, query_index=index, source_unit=None)
        prompts.append(prompt)
        units[f"c{index}-q{index}"] = _row(names, levels, cond, rng, mc)

    for qi in range(6):
        link = f"L{qi}"
        features["questions"][f"{link}|1"] = {"anchored": qi % 2 == 0, "anchors": {}}
        for lang in ("en", "ja"):
            features["token_counts"]["passage"][f"{lang}|{link}|1"] = 100 if lang == "en" else 140
            features["token_counts"]["question"][f"{lang}|{link}|1"] = 10
        for pair in ("ja>en", "en>ja"):
            common = {"pair": pair, "cluster": link, "question_number": 1,
                      "needle_language": pair.split(">")[0], "family_id": f"dev|{pair}|{link}|1"}
            for cond in ("MN", "CX"):
                pid = f"dev|{pair}|{link}|1|{cond}"
                features["prompt_overlap"][pid] = {"share": 0.4 if cond == "MN" else 0.0}
                add({"prompt_id": pid, "role": "dev", "condition": cond, **common}, cond, True)
            add({"prompt_id": f"dev-absent|{pair}|{link}|1|CX", "role": "dev-absent",
                 "condition": "CX", **common}, "absent", True)
        for lang in ("en", "ja"):
            add({"prompt_id": f"dev-literal|{lang}>{lang}|{link}|1|ML", "role": "dev-literal",
                 "pair": f"{lang}>{lang}", "condition": "ML", "family_id": f"ml|{lang}|{link}|1",
                 "cluster": link, "question_number": 1, "needle_language": lang}, "ML", False)
    artifact = {"prompts": prompts, "features": features, "contexts": contexts,
                "source": {"k1_smoke_units": []}}
    return artifact, dhs.Results(names, units)


def _row(names: list[str], levels: dict[str, float], cond: str, rng: np.random.Generator,
         mc: bool) -> dict[str, Any]:
    recall = np.zeros((2, len(names)))
    target = levels.get(f"T:{cond}", 40.0)
    for i, name in enumerate(names):
        if name.startswith("T:"):
            value = target
        elif name.startswith("rand"):
            value = levels["rand"]
        elif name == "LEX":
            value = levels.get(f"LEX:{cond}", levels["rand"])
        elif name.startswith("N:"):
            value = target - levels.get("null_drop", 2.0)
        else:
            value = target
        recall[:, i] = np.clip(value + rng.normal(0, 0.5), 0, 100)
    correct = int(rng.random() < levels.get(f"acc:{cond}", 0.6))
    scores = np.zeros(4) if mc else np.full(4, np.nan)
    if mc:
        scores[0 if correct else 1] = 1.0
    return {"recall": recall, "ties": np.zeros(len(names), dtype=np.int64), "max_selected": 0,
            "k_blocks": 256, "mc_scores": scores, "mc_correct": 0 if mc else -1}


def case_statistics() -> dict[str, Any]:
    failures: list[str] = []
    seeds = [42, 43, 44]
    reads = {}
    for label, levels, expected in (
        ("wide", {"T:MN": 45, "T:CX": 40, "T:ML": 80, "rand": 12, "LEX:MN": 30,
                  "acc:CX": 0.95, "acc:absent": 0.1, "acc:MN": 0.95}, "NEGATIVE_CAPABLE"),
        ("narrow", {"T:MN": 30, "T:CX": 27, "T:ML": 70, "rand": 12,
                    "acc:CX": 0.95, "acc:absent": 0.1, "acc:MN": 0.95}, "GO_ONLY_CAPABLE"),
        ("flat", {"T:MN": 17, "T:CX": 15, "T:ML": 60, "rand": 12,
                  "acc:CX": 0.95, "acc:absent": 0.1, "acc:MN": 0.95}, "NOT_VIABLE"),
    ):
        artifact, results = _results_fixture(levels, seeds)
        report = dhs.analyse(artifact, results, seeds=seeds, replicates=300)
        verdict = report["decisions"]["lane_class"]
        reads[label] = {"lane_class": verdict, "h1": report["decisions"]["h1_cx_points"],
                        "lexical_confound": report["decisions"]["lexical_confound"],
                        "floor": report["decisions"]["floor_candidate"]}
        _check(verdict == expected, f"{label}: {verdict}, expected {expected}", failures)
    _check(reads["wide"]["lexical_confound"] == "PRESENT",
           "a literal selector with MN-only recall did not flag the anchor confound", failures)
    # Retention: an exact copy of the target keeps G = 1, random keeps 0.
    group = dhs.Group.of([{"pair": "a", "cluster": f"c{i}"} for i in range(5)])
    tgt, rnd = [40.0] * 5, [10.0] * 5
    _check(abs(dhs.retention_interval(tgt, tgt, rnd, group, 200)["point"] - 1.0) < 1e-12
           and abs(dhs.retention_interval(rnd, tgt, rnd, group, 200)["point"]) < 1e-12,
           "retention G is wrong", failures)
    # Null verdict rules.
    good = {"0.25": {"english_ml": {"v1_pass": True, "loss_seed_mean": 0.4},
                     "xi": {"point": 0.1}, "xi_rel": {"evaluable": True, "point": 0.01}},
            "0.5": {"english_ml": {"v1_pass": True, "loss_seed_mean": 3.0},
                    "xi": {"point": 1.0}, "xi_rel": {"evaluable": True, "point": 0.05}},
            "2": {"english_ml": {"v1_pass": False, "loss_seed_mean": 9.0},
                  "xi": {"point": 9.0}, "xi_rel": {"evaluable": True, "point": 0.5}}}
    _check(dhs.null_verdict(good)["verdict"] == "CENTRED", "null verdict CENTRED", failures)
    near_copy = copy.deepcopy(good)
    near_copy["0.5"]["english_ml"]["loss_seed_mean"] = 2.0
    _check(dhs.null_verdict(near_copy)["verdict"] == "NOT_EVALUABLE",
           "a null tested only on near-exact copies of the target was not NOT_EVALUABLE",
           failures)
    bad = copy.deepcopy(good)
    bad["0.5"]["xi"]["point"] = 3.0
    _check(dhs.null_verdict(bad)["verdict"] == "NOT_CENTRED", "null verdict NOT_CENTRED",
           failures)
    none = copy.deepcopy(good)
    for sigma in ("0.25", "0.5"):
        none[sigma]["english_ml"]["v1_pass"] = False
    _check(dhs.null_verdict(none)["verdict"] == "NOT_EVALUABLE", "null verdict NOT_EVALUABLE",
           failures)
    # Combined read.
    base = {"lexical_confound": "ABSENT", "entity_control": "SUFFICIENT",
            "null_calibration": {"hs": "CENTRED", "mp": "CENTRED"},
            "floor_candidate": "VIABLE", "h2_status": "PASS"}
    combos = {
        ("NEGATIVE_CAPABLE", "NEGATIVE_CAPABLE"): ("NEGATIVE_CAPABLE_V3", "qwen3-0.6b-base"),
        ("GO_ONLY_CAPABLE", "NEGATIVE_CAPABLE"): ("NEGATIVE_CAPABLE_V3", "qwen3.5-4b-base"),
        ("GO_ONLY_CAPABLE", "NOT_VIABLE"): ("GO_ONLY_V3", "qwen3-0.6b-base"),
        ("NOT_VIABLE", "NOT_VIABLE"): ("NO_K1_V3", None),
        ("NOT_VIABLE", "INVALID"): ("INVALID", None),
        ("INVALID", "NEGATIVE_CAPABLE"): ("INVALID", None),
        ("INVALID", "GO_ONLY_CAPABLE"): ("INVALID", None),
    }
    for (small, large), (design, chosen) in combos.items():
        combined = dhs.combined_recommendation({
            "qwen3-0.6b-base": {**base, "lane_class": small},
            "qwen3.5-4b-base": {**base, "lane_class": large}})
        _check((combined["design"], combined["base"]) == (design, chosen),
               f"combined read for {small}/{large}: {combined['design']}", failures)
    _check(dhs.combined_recommendation({"qwen3-0.6b-base": {**base, "lane_class": "NOT_VIABLE"}}
                                       )["design"] == "INCOMPLETE",
           "a missing lane is not INCOMPLETE", failures)
    _check(dhs.combined_recommendation({"qwen3-0.6b-base": {**base, "lane_class": "INVALID"}}
                                       )["design"] == "INVALID",
           "an INVALID 0.6B lane without the 4B lane is not INVALID", failures)
    clean = dhs.combined_recommendation({"qwen3-0.6b-base": {**base,
                                                             "lane_class": "NEGATIVE_CAPABLE"},
                                         "qwen3.5-4b-base": {**base, "lane_class": "NOT_VIABLE"}})
    _check("an entity-controlled question set (D26)" in clean["requirements"],
           "a lexical confound read ABSENT removed D26's entity-controlled set", failures)
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, "reads": reads}


def case_end_to_end(tmp: Path) -> dict[str, Any]:
    failures: list[str] = []
    run = TinyRun(tmp / "e2e")
    out: dict[str, Any] = {}
    # Fail-closed startup.
    bad = run.run("tiny-attention", tmp / "bad-digest", bundle_sha="0" * 64)
    _check(bad.returncode == 2, f"a bundle digest mismatch exited {bad.returncode}", failures)
    seeds = run.run("tiny-attention", tmp / "bad-seeds", seeds=("1", "2", "3"))
    _check(seeds.returncode == 2, f"wrong seeds exited {seeds.returncode}", failures)
    for lane_id in ("tiny-attention", "tiny-hybrid"):
        run_dir = tmp / f"full-{lane_id}"
        started = time.perf_counter()
        done = run.run(lane_id, run_dir)
        elapsed = time.perf_counter() - started
        if done.returncode != 0:
            failures.append(f"{lane_id}: exit {done.returncode}: {done.stderr[-1500:]}")
            continue
        receipt = receipt_of(run_dir)
        _check(receipt["status"] == "PRECHECK_COMPLETE", f"{lane_id}: status", failures)
        _check(receipt["coverage"]["within_budget"], f"{lane_id}: budget", failures)
        _check(receipt["attention_layers"] == list(dhd.lane_of(lane_id).attention_layers),
               f"{lane_id}: attention layers", failures)
        out[lane_id] = {"seconds": round(elapsed, 1), "decisions": receipt["decisions"],
                        "units": receipt["coverage"]["units"],
                        "dev_artifact_sha256": receipt["hashes"]["dev_artifact_sha256"]}
    # Interrupt after the first chunk, then continue in a fresh job directory.
    lane_id = "tiny-hybrid"
    run_dir = tmp / "interrupted"
    run_dir.mkdir(parents=True)
    run.batch_files(lane_id, run_dir)
    process = subprocess.Popen(run.argv(lane_id, run_dir), env=run.env(run_dir),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    eval_dir = run_dir / "dense-precheck" / "checkpoints" / "eval"
    deadline = time.time() + 900
    while time.time() < deadline and process.poll() is None:
        if list(eval_dir.glob("*/chunk-*.npz")):
            process.send_signal(signal.SIGUSR1)
            break
        time.sleep(0.05)
    stdout, stderr = process.communicate(timeout=900)
    marker = run_dir / "checkpoint.ready"
    _check(process.returncode == 75, f"interrupted run exited {process.returncode}: "
                                     f"{stderr[-800:]}", failures)
    _check(marker.is_file() and "trigger=SIGUSR1" in marker.read_text(),
           "the interrupted run wrote no marker with the trigger line", failures)
    saved = run_dir / "dense-precheck" / "checkpoints"
    # The same continuation without the batch script's resume receipt is refused.
    unreceipted = tmp / "continued-no-receipt"
    (unreceipted / "dense-precheck").mkdir(parents=True)
    if saved.is_dir():
        shutil.copytree(saved, unreceipted / "dense-precheck" / "checkpoints")
    refused_cont = run.run(lane_id, unreceipted, predecessor="1", resume_receipt=False)
    _check(refused_cont.returncode == 2, "a continuation without its resume receipt exited "
           f"{refused_cont.returncode}", failures)
    resumed = tmp / "continued"
    (resumed / "dense-precheck").mkdir(parents=True)
    if saved.is_dir():
        shutil.copytree(saved, resumed / "dense-precheck" / "checkpoints")
    cont = run.run(lane_id, resumed, predecessor="1")
    _check(cont.returncode == 0, f"continuation exited {cont.returncode}: {cont.stderr[-800:]}",
           failures)
    if cont.returncode == 0 and lane_id in out:
        full = receipt_of(tmp / f"full-{lane_id}")
        again = receipt_of(resumed)
        _check(full["report"]["headroom"] == again["report"]["headroom"]
               and full["decisions"] == again["decisions"],
               "the continuation's read differs from the uninterrupted run", failures)
        _check(full["hashes"]["job"]["kind"] == "fresh"
               and again["hashes"]["job"] == {"kind": "continuation",
                                              "predecessor_job_id": "1", "minutes": 0},
               f"job kinds recorded {full['hashes']['job']} and {again['hashes']['job']}",
               failures)
    # A continuation whose artifact differs is an integrity failure.
    forged = tmp / "forged"
    (forged / "dense-precheck" / "checkpoints").mkdir(parents=True)
    (forged / "dense-precheck" / "checkpoints" / "dev-artifact.sha256").write_text("0" * 64)
    refused = run.run(lane_id, forged, predecessor="1")
    _check(refused.returncode == 3, f"a forged artifact pin exited {refused.returncode}",
           failures)
    del stdout
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, **out}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-end-to-end", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    dhd.block_gpu_only_kernels()  # CPU only (see make_tiny_hybrid)
    started = time.perf_counter()
    cases: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="dense-doctor-") as tmp_name:
        tmp = Path(tmp_name)
        runners = [("codecs", case_codecs), ("features", case_features),
                   ("derive", lambda: case_derive(tmp / "derive")),
                   ("statistics", case_statistics),
                   ("selectors", lambda: case_selectors(tmp / "selectors")),
                   ("multiple_choice", lambda: case_multiple_choice(tmp / "mc"))]
        if not args.skip_end_to_end:
            runners.append(("end_to_end", lambda: case_end_to_end(tmp / "e2e")))
        for name, runner in runners:
            try:
                cases[name] = runner()
            except Exception as exc:  # noqa: BLE001 - a crashing case is a failing case
                cases[name] = {"status": "FAIL", "failures": [f"{type(exc).__name__}: {exc}"]}
    status = ("DENSE_DOCTOR_PASS" if all(c["status"] == "PASS" for c in cases.values())
              else "DENSE_DOCTOR_FAIL")
    receipt = {"doctor": DOCTOR_NAME, "experiment_id": dhd.EXPERIMENT_ID, "status": status,
               "evidence_grade": EVIDENCE_GRADE, "numbers_are_synthetic": True,
               "case_status": {name: c["status"] for name, c in cases.items()},
               "cases": cases, "seconds": round(time.perf_counter() - started, 1),
               "code_sha256": {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()
                                                    ).hexdigest()
                               for name in ("harness/dense_headroom_data.py",
                                            "harness/dense_headroom_stats.py",
                                            "harness/dense_headroom_torch.py",
                                            "scripts/run_dense_headroom_precheck.py",
                                            "scripts/run_dense_headroom_precheck_doctor.py")}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": status, "case_status": receipt["case_status"]}))
    return 0 if status == "DENSE_DOCTOR_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
