#!/usr/bin/env python3
"""CPU doctor for the Q3 K1 localization screen on a tiny random Qwen3 model.

Exercises every K1 object before any GPU job: the capture path against eager
attention (including a KV-cache continuation), the hs and mp targets against a
NumPy reference, block selection and the union reference against brute force,
the indexer gradient against finite differences, the verdict rules on
hand-made tables, the data objects (ParaDocs filter, filters, dedup, packing,
contexts, codec, fail-closed reads), and the GPU entry point end to end on CPU:
a digest mismatch exits 2; smoke, headroom-dev, the three resume legs (with a
real SIGUSR1 to the PID-1 parent and a stale marker), 0a-k1 and the extension
all run on a synthetic bundle built by the real builder code.

Every number is a synthetic-case number. A PASS proves executability and gate
semantics only; it says nothing about Qwen3-0.6B-Base, the data or the claim.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
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

from harness import sparse_indexer_data as sid  # noqa: E402
from harness import sparse_indexer_k1_stats as k1s  # noqa: E402
from harness import translation_supervised_indexer as tsi  # noqa: E402

DOCTOR_NAME = "q3-k1-localization-screen-cpu-doctor"
EVIDENCE_GRADE = (
    "EXECUTABILITY_AND_GATE_SEMANTICS_ONLY: a tiny randomly initialised Qwen3 model, a "
    "byte-level stand-in tokenizer and a synthetic bundle built by the real builder code. "
    "Nothing here touches Qwen3-0.6B-Base, Belebele, FineWeb or ParaDocs."
)
ENTRY = PROJECT_ROOT / "scripts" / "run_sparse_indexer_phase0a.py"
CONTRACT = (PROJECT_ROOT / "experiments" / "architectures"
            / "translation-supervised-sparse-indexer-k1-screen.yaml")
EXPERIMENT_ID = "q3-k1-localization-screen-v1"
TINY_LAYERS = 4


# --------------------------------------------------------------------------- #
# Fixtures shared with the tests
# --------------------------------------------------------------------------- #


class ByteTokenizer:
    """Deterministic byte-level stand-in tokenizer (ids 2..vocab-1)."""

    def __init__(self, vocab: int = 512) -> None:
        self.vocab = vocab
        self.sha256 = hashlib.sha256(f"byte-tokenizer-{vocab}".encode()).hexdigest()

    def encode(self, text: str) -> list[int]:
        return [2 + (b % (self.vocab - 2)) for b in text.encode("utf-8")]

    def encode_batch(self, texts: list[str]) -> list[list[int]]:
        return [self.encode(t) for t in texts]


def make_tiny_model(directory: Path, seed: int = 0, layers: int = TINY_LAYERS) -> Path:
    import torch
    from transformers import Qwen3Config, Qwen3ForCausalLM

    torch.manual_seed(seed)
    config = Qwen3Config(
        vocab_size=512, hidden_size=64, intermediate_size=128, num_hidden_layers=layers,
        num_attention_heads=4, num_key_value_heads=2, head_dim=16,
        max_position_embeddings=4096, rope_theta=1_000_000.0, tie_word_embeddings=True,
        bos_token_id=1, eos_token_id=1, pad_token_id=1,
    )
    model = Qwen3ForCausalLM(config)
    directory.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(directory, safe_serialization=True)
    return directory


def _words(rng: np.random.Generator, n: int, alphabet: str = "abcdefghijklmnopqrstuvwxyz") -> str:
    return " ".join("".join(rng.choice(list(alphabet), size=rng.integers(2, 7)))
                    for _ in range(n))


def synthetic_sources(seed: int = 7, links: int = 16) -> Any:
    """In-memory raw sources shaped like the real ones (18 Belebele languages etc.)."""

    from scripts.build_sparse_indexer_k1_bundle import RawSources

    rng = np.random.default_rng(seed)
    belebele: dict[str, list[sid.BelebeleRow]] = {code: [] for code in sid.BELEBELE_LANGUAGES}
    for link_index in range(links):
        link = f"https://example.org/passage/{link_index}"
        for qnum in (1, 2):
            correct = int(rng.integers(1, 5))
            for code in sid.BELEBELE_LANGUAGES:
                belebele[code].append(sid.BelebeleRow(
                    link=link, question_number=qnum,
                    passage=f"{code} " + _words(rng, 8) + ". " + _words(rng, 6) + ".",
                    question=f"{code} " + _words(rng, 3) + "?",
                    options=tuple(_words(rng, 2) for _ in range(4)),  # type: ignore[arg-type]
                    correct=correct))
    mono = {code: [(f"{code}-{i}", _words(rng, int(rng.integers(5, 30)))) for i in range(60)]
            for code in sid.MONOLINGUAL_TRAINING}
    bilingual = {}
    for pair in sid.BILINGUAL_PAIRS:
        rows = [{"doc_id": f"{pair}:{i}", "en": _words(rng, 6), "x": _words(rng, 6)}
                for i in range(60)]
        bilingual[pair] = rows
    bilingual["en-th"].insert(0, {"doc_id": "en-th:greek", "en": "alpha",
                                  "x": "αβγδε ζηθ ικλ μνξ"})
    bilingual["en-de"].insert(0, {"doc_id": "en-de:italian", "en": "the session",
                                  "x": "il questo della sono anche nella"})
    haystack = {code: [(f"h{code}-{i}", _words(rng, int(rng.integers(3, 12))))
                       for i in range(80)] for code in sid.NEEDLE_LANGUAGES}
    sources = {code: f"synthetic:{code}" for code in sid.NEEDLE_LANGUAGES}
    return RawSources(belebele, mono, bilingual, haystack, sources,
                      {"sources": {"synthetic": True}}, "0" * 64)


def tiny_params() -> Any:
    from scripts.build_sparse_indexer_k1_bundle import BuildParams

    return BuildParams(
        sequence_length=64, context_length=128, sink=1, bilingual_train=6, mono_train=6,
        bilingual_dev=2, mono_dev=2, mono_item_max=32, mono_min_tokens=2, haystack_min=4,
        haystack_max=60, haystack_docs=60, haystack_draw=24, dev_families_per_pair=2,
        ml_en=4, ml_x=4, absent=6, collect_margin=2.5, bilingual_side_max=24,
        max_bytes=64 * 1024**2)


def build_tiny_bundle(directory: Path) -> tuple[Path, str]:
    from scripts.build_sparse_indexer_k1_bundle import assemble_bundle, write_bundle

    tokenizer = ByteTokenizer()
    bundle = assemble_bundle(synthetic_sources(), tokenizer, tiny_params())
    path = directory / "k1-bundle-tiny.json"
    summary = write_bundle(bundle, path, tiny_params().max_bytes)
    return path, summary["sha256"]


def freeze_tiny_prereg(root: Path) -> tuple[Path, str, Path]:
    from scripts import preregister

    prereg = root / "program" / "preregistrations" / f"{EXPERIMENT_ID}.md"
    prereg.parent.mkdir(parents=True, exist_ok=True)
    prereg.write_text("# doctor stand-in preregistration\n\nSynthetic only.\n",
                      encoding="utf-8")
    ledger = root / "program" / "preregistrations" / "ledger.jsonl"
    preregister.freeze(prereg, EXPERIMENT_ID, ledger=ledger, root=root)
    return prereg, preregister.sha256_file(prereg), ledger


def write_stand_in_receipt(path: Path) -> str:
    payload = {"model_id": "qwen3-0.6b-base",
               "revision": "da87bfb608c14b7cf20ba1ce41287e8de496c0cd",
               "files": [], "note": "doctor stand-in; the real receipt is hashed in the job"}
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TinyRun:
    """Everything a CPU entry-point run needs."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.model = make_tiny_model(root / "model")
        self.bundle, self.bundle_sha = build_tiny_bundle(root)
        self.prereg, self.prereg_sha, self.ledger = freeze_tiny_prereg(root / "repo")
        self.receipt = root / "receipt.json"
        self.receipt_sha = write_stand_in_receipt(self.receipt)

    def argv(self, phase: str, run_dir: Path, *extra: str, bundle_sha: str | None = None,
             workers: int = 2) -> list[str]:
        return [
            sys.executable, str(ENTRY), str(CONTRACT), "--phase", phase,
            "--output-dir", str(run_dir / "phase-0a-k1"),
            "--evidence", str(self.bundle),
            "--expected-evidence-sha256", bundle_sha or self.bundle_sha,
            "--model-dir", str(self.model),
            "--receipt", str(self.receipt), "--expected-receipt-sha256", self.receipt_sha,
            "--preregistration", str(self.prereg),
            "--expected-preregistration-sha256", self.prereg_sha,
            "--ledger", str(self.ledger), "--ledger-root", str(self.root / "repo"),
            "--seeds", "42", "43", "44", "--workers", str(workers),
            "--profile", "tiny", "--device", "cpu",
            "--stage-dir", str(run_dir / "stage"), *extra,
        ]

    @staticmethod
    def env(run_dir: Path) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith("COTCODEC_")}
        env["COTCODEC_CHECKPOINT_MARKER"] = str(run_dir / "checkpoint.ready")
        env["OMP_NUM_THREADS"] = "2"
        env["PYTHONHASHSEED"] = "0"
        return env

    def run(self, phase: str, run_dir: Path, *extra: str, timeout: int = 900,
            **kwargs: Any) -> subprocess.CompletedProcess:
        run_dir.mkdir(parents=True, exist_ok=True)
        return subprocess.run(self.argv(phase, run_dir, *extra, **kwargs), env=self.env(run_dir),
                              capture_output=True, text=True, timeout=timeout, check=False)


def receipt_of(run_dir: Path, name: str = "receipt.json") -> dict[str, Any]:
    return json.loads((run_dir / "phase-0a-k1" / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Cases
# --------------------------------------------------------------------------- #


def case_capture_vs_eager(tmp: Path) -> dict[str, Any]:
    import torch

    from harness import sparse_indexer_torch as sit

    sit.set_determinism(allow_tf32=False)
    model_dir = make_tiny_model(tmp / "capture-model", seed=3)
    capture = sit.load_teacher(model_dir, "cpu", dtype=torch.float32)
    eager = sit.load_teacher(model_dir, "cpu", dtype=torch.float32, attn_implementation="eager")
    generator = torch.Generator().manual_seed(0)
    ids = torch.randint(2, 512, (1, 96), generator=generator)
    layers = range(capture.config.num_hidden_layers)
    scaling = capture.config.head_dim ** -0.5
    with sit.CaptureSession(capture, layers) as cap, torch.no_grad():
        out_c = capture.model(input_ids=ids, use_cache=False)
        full = {layer: (cap.query[layer][0], cap.key[layer][0]) for layer in layers}
    with torch.no_grad():
        out_e = eager.model(input_ids=ids, use_cache=False, output_attentions=True)
    rows = torch.arange(96)
    worst = max(float((sit.head_probs_rows(*full[layer], rows, scaling)
                       - out_e.attentions[layer][0]).abs().max()) for layer in layers)
    hidden = float((out_c.last_hidden_state - out_e.last_hidden_state).abs().max())
    from transformers import DynamicCache

    cache = DynamicCache(config=capture.config)
    with torch.no_grad():
        capture.model(input_ids=ids[:, :80], use_cache=True, past_key_values=cache)
        with sit.CaptureSession(capture, layers) as cap:
            capture.model(input_ids=ids[:, 80:], use_cache=True, past_key_values=cache)
            continued = {layer: (cap.query[layer][0], cap.key[layer][0]) for layer in layers}
    tail = torch.arange(80, 96)
    worst_cache = max(float((sit.head_probs_rows(*continued[layer], tail, scaling)
                             - out_e.attentions[layer][0][:, 80:]).abs().max())
                      for layer in layers)
    gates = {"capture_equals_eager": worst <= 1e-5,
             "kv_cache_continuation_equals_eager": worst_cache <= 1e-5,
             "hidden_states_agree": hidden <= 1e-4}
    return {"max_abs_prob_error": worst, "max_abs_prob_error_kv_cache": worst_cache,
            "max_abs_hidden_error": hidden, "gates": gates}


def numpy_block_reference(probs: np.ndarray, block: int = 4) -> dict[str, np.ndarray]:
    """Reference hs and mp from the NumPy harness head-sum plus explicit pooling."""

    heads, length, _ = probs.shape
    head_sum = tsi.aggregate_target(probs[None], "hs")[0]
    n_blocks = length // block
    blocks = head_sum[:, : n_blocks * block].reshape(length, n_blocks, block)
    valid = (np.arange(n_blocks)[None, :] * block + block - 1) <= np.arange(length)[:, None]
    out = {}
    for name, pooled in (("hs", blocks.sum(-1)), ("mp", blocks.max(-1))):
        masked = np.where(valid, pooled, 0.0)
        total = masked.sum(-1, keepdims=True)
        out[name] = np.where(total > 0, masked / np.where(total > 0, total, 1.0), 0.0)
    out["valid"] = valid
    return out


def random_causal_probs(rng: np.random.Generator, heads: int, length: int) -> np.ndarray:
    scores = rng.normal(size=(heads, length, length)) * 2.0
    mask = np.tril(np.ones((length, length), dtype=bool))
    scores = np.where(mask, scores, -np.inf)
    scores -= scores.max(-1, keepdims=True)
    exp = np.exp(scores)
    return exp / exp.sum(-1, keepdims=True)


def case_targets_vs_numpy() -> dict[str, Any]:
    import torch

    from harness import sparse_indexer_torch as sit

    rng = np.random.default_rng(11)
    worst = 0.0
    for length in (12, 23, 40):
        probs = random_causal_probs(rng, 4, length)
        reference = numpy_block_reference(probs)
        rows = torch.arange(length)
        mine = sit.block_targets(torch.as_tensor(probs), rows)
        for name in ("hs", "mp"):
            worst = max(worst, float(np.abs(mine[name].numpy() - reference[name]).max()))
        assert np.array_equal(mine["valid"].numpy(), reference["valid"])
    mp_differs = bool(np.abs(reference["hs"] - reference["mp"]).max() > 1e-3)
    gates = {"targets_equal_numpy_reference": worst <= 1e-9, "mp_is_not_hs": mp_differs}
    return {"max_abs_error": worst, "gates": gates}


def case_selection_brute_force() -> dict[str, Any]:
    import torch

    from harness import sparse_indexer_torch as sit

    rng = np.random.default_rng(5)
    mismatches = 0
    for _ in range(25):
        n_rows, n_blocks, k = 6, 9, 4
        scores = np.round(rng.normal(size=(n_rows, n_blocks)), 1)
        scores[:, ::3] = 0.0
        rows = rng.integers(3, 4 * n_blocks + 2, size=n_rows)
        valid = (np.arange(n_blocks)[None, :] * 4 + 3) <= rows[:, None]
        chosen = sit.select_top_blocks(torch.as_tensor(scores), torch.as_tensor(valid), k)
        for r in range(n_rows):
            eligible = sorted((b for b in range(n_blocks) if valid[r, b]),
                              key=lambda b, r=r: (-scores[r, b], b))[:k]
            expected = eligible + [-1] * (k - len(eligible))
            mismatches += int(chosen[r].tolist() != expected)
    union_mismatch = 0
    for _ in range(10):
        length, heads, k = 20, 3, 4
        probs = random_causal_probs(rng, heads, length)
        brute = tsi.brute_force_union_top_k(probs, k)
        needle = (3, 8)
        rows = np.arange(12, 20)
        expected = brute[np.ix_(rows, np.arange(*needle))].sum(1) / (needle[1] - needle[0])
        mine = sit.union_topk_recall(torch.as_tensor(probs[:, rows]), torch.as_tensor(rows), k,
                                     *needle).numpy()
        union_mismatch += int(not np.allclose(mine, expected))
    random_errors = []
    for n_complete, k, needle in ((8, 3, (5, 14)), (6, 2, (0, 7)), (10, 10, (2, 30))):
        row = n_complete * 4 + 1
        exact = []
        for subset in itertools.combinations(range(n_complete), min(k, n_complete)):
            covered = sum(len(set(range(b * 4, b * 4 + 4)) & set(range(*needle)))
                          for b in subset)
            exact.append(covered / (needle[1] - needle[0]))
        mine = float(sit.random_block_recall(torch.as_tensor([row]), *needle, k_blocks=k)[0])
        random_errors.append(abs(mine - float(np.mean(exact))))
    gates = {"block_selection_equals_brute_force": mismatches == 0,
             "union_reference_equals_brute_force": union_mismatch == 0,
             "analytic_random_equals_enumeration": max(random_errors) <= 1e-6}
    return {"selection_mismatches": mismatches, "union_mismatches": union_mismatch,
            "random_max_error": max(random_errors), "gates": gates}


def case_gradient_check() -> dict[str, Any]:
    import torch

    from harness import sparse_indexer_torch as sit

    spec = sit.IndexerSpec(d_model=8, heads=2, dim=4, rope_dims=4)
    torch.manual_seed(0)
    indexer = sit.BlockIndexer(spec, torch.Generator().manual_seed(1)).double()
    with torch.no_grad():
        indexer.gate_w.normal_(0.0, 0.3)
        indexer.q_norm.uniform_(0.5, 1.5)
    hidden = torch.randn(16, 8, dtype=torch.float64)
    rows = torch.arange(16)
    probs = torch.as_tensor(random_causal_probs(np.random.default_rng(2), 3, 16))
    target = sit.block_targets(probs, rows)["hs"]

    def loss_fn() -> torch.Tensor:
        scores, valid = indexer(hidden, rows)
        return sit.kl_block_loss(target, scores, valid)[0]

    loss = loss_fn()
    loss.backward()
    worst = 0.0
    rng = np.random.default_rng(3)
    for name, param in indexer.named_parameters():
        flat = param.detach().view(-1)
        for index in rng.choice(flat.numel(), size=min(6, flat.numel()), replace=False):
            original = float(flat[index])
            with torch.no_grad():
                flat[index] = original + 1e-6
                up = float(loss_fn())
                flat[index] = original - 1e-6
                down = float(loss_fn())
                flat[index] = original
            numeric = (up - down) / 2e-6
            analytic = float(param.grad.view(-1)[index])
            scale = max(abs(numeric), abs(analytic), 1e-8)
            if abs(numeric) > 1e-7 or abs(analytic) > 1e-7:
                worst = max(worst, abs(numeric - analytic) / scale)
            _ = name
    return {"max_relative_error": worst, "gates": {"gradient_matches": worst <= 1e-4}}


def _table(pairs: int, clusters: int, seeds: int, means: dict[str, tuple[float, float]],
           noise: float, rng: np.random.Generator) -> k1s.FamilyTable:
    pair = np.repeat(np.arange(pairs), clusters)
    cluster = np.tile(np.arange(clusters), pairs)
    n = pair.size

    def draw(mean: float, shape: tuple[int, ...]) -> np.ndarray:
        return np.clip(mean + rng.normal(0.0, noise, size=shape), 0.0, 100.0)

    return k1s.FamilyTable(
        pair=pair, cluster=cluster,
        ind_mn=draw(means["ind"][0], (seeds, n)), ind_cx=draw(means["ind"][1], (seeds, n)),
        tgt_mn=draw(means["tgt"][0], (n,)), tgt_cx=draw(means["tgt"][1], (n,)),
        rand_mn=np.full(n, means["rand"][0]), rand_cx=np.full(n, means["rand"][1]))


def _read(name: str, table: k1s.FamilyTable, *, ml: tuple[float, float] = (90.0, 92.0),
          integrity: bool = True) -> k1s.TargetRead:
    return k1s.TargetRead(name, k1s.xi_interval(table, replicates=2000),
                          k1s.xi_rel_interval(table, replicates=2000),
                          k1s.AdequacyRead((ml[0],) * table.n_seeds, ml[1]), integrity)


def case_verdict_tables() -> dict[str, Any]:
    rng = np.random.default_rng(42)
    good = k1s.HeadroomRead(
        60.0,
        k1s.Interval(55.0, (55.0,), 0, 1, 1, 50.0, 60.0, 5, 50.0, 60.0, 2000, True),
        k1s.Interval(20.0, (20.0,), 0, 1, 1, 10.0, 30.0, 10, 10.0, 30.0, 2000, True))
    low_h1 = k1s.HeadroomRead(5.0, good.h2a, good.h2b)
    target = {"tgt": (80.0, 70.0), "rand": (10.0, 10.0)}
    scenarios = {
        "go": ({**target, "ind": (78.0, 50.0)}, 1.0, good, "GO"),
        "negative": ({**target, "ind": (77.0, 67.0)}, 1.0, good, "NEGATIVE"),
        "uniformly_weaker_is_not_a_go": ({**target, "ind": (45.0, 40.0)}, 1.0, good,
                                         "NEGATIVE"),
        "masked_deficit_inconclusive": ({**target, "ind": (52.0, 34.0)}, 1.0, good,
                                        "INCONCLUSIVE"),
        "noisy_negative_inconclusive": ({**target, "ind": (77.0, 67.0)}, 60.0, good,
                                        "INCONCLUSIVE"),
        "no_headroom_uninterpretable": ({**target, "ind": (77.0, 67.0)}, 1.0, low_h1,
                                        "UNINTERPRETABLE"),
    }
    outcomes = {}
    for name, (means, noise, headroom, expected) in scenarios.items():
        reads = [_read(t, _table(14, 30, 3, means, noise, rng)) for t in ("hs", "mp")]
        verdict = k1s.k1_verdict(reads, headroom).verdict
        outcomes[name] = {"verdict": verdict, "expected": expected,
                          "xi": reads[0].xi.point, "xi_rel": reads[0].xi_rel.point}
    table = _table(14, 30, 3, {**target, "ind": (77.0, 67.0)}, 1.0, rng)
    hold = k1s.k1_verdict([_read("hs", table, ml=(95.0, 92.0))], good).verdict
    void = k1s.k1_verdict([_read("hs", table, integrity=False)], good).verdict
    outcomes["bug_tell_holds"] = {"verdict": hold, "expected": "HOLD"}
    outcomes["integrity_voids"] = {"verdict": void, "expected": "VOID"}
    gates = {name: row["verdict"] == row["expected"] for name, row in outcomes.items()}
    return {"outcomes": outcomes, "gates": gates}


def case_data_objects(tmp: Path) -> dict[str, Any]:
    gates: dict[str, bool] = {}
    base = {"similarity_one": "1", "similarity_two": "1", "collection": "c",
            "src_paragraph_id": "1", "tgt_paragraph_id": "1", "src_sentence_id": "1",
            "tgt_sentence_id": "1", "src_language_id": "0.9", "tgt_language_id": "0.9",
            "frequency": "1", "src_docid": "d", "tgt_docid": "e"}
    rows = [
        {**base, "src": "a", "tgt": "x", "src_start_index": "0", "src_end_index": "5",
         "tgt_start_index": "0", "tgt_end_index": "5"},
        # tgt side jumps far ahead: upstream's quirk still joins it
        {**base, "src": "b", "tgt": "y", "src_start_index": "6", "src_end_index": "9",
         "tgt_start_index": "90", "tgt_end_index": "95"},
        {**base, "src": "c", "tgt": "z", "src_start_index": "40", "src_end_index": "45",
         "tgt_start_index": "96", "tgt_end_index": "99"},
        {**base, "src": "d", "tgt": "w", "src_start_index": "46", "src_end_index": "50",
         "tgt_start_index": "100", "tgt_end_index": "104", "frequency": "500"},
    ]
    stats = sid.ParadocsStats()
    docs = list(sid.paradocs_documents(rows, sid.ParadocsFilter(), stats))
    gates["paradocs_quirk_and_breaks"] = (
        [len(d) for d in docs] == [2] and stats.breaks_frequency == 1)
    packed, used = sid.pack_sequences([[5, 6, 7], [8, 9], [10, 11, 12, 13], [14]], 2,
                                      length=6, sink=1)
    gates["packing"] = packed.tolist() == [[1, 5, 6, 7, 1, 8], [1, 10, 11, 12, 13, 1]] and (
        used == 4)
    context = sid.build_context([90, 91, 92], [("a", [5] * 10), ("b", [6] * 10), ("c", [7] * 10)],
                                0.5, [3], length=24, sink=1)
    gates["context_exact_length_and_needle"] = (
        len(context.tokens) == 24
        and context.tokens[context.needle_start : context.needle_end].tolist() == [90, 91, 92])
    eval_tokens = list(range(100, 160))
    index = sid.DedupIndex([eval_tokens])
    dstats = sid.DedupStats()
    exact_hit = not index.check([1, 2] + eval_tokens[:55] + [3], dstats)
    near = eval_tokens[:30] + [999] + eval_tokens[31:]
    minhash_hit = index.max_jaccard(near) >= sid.MINHASH_THRESHOLD
    clean = index.check(list(range(500, 560)), sid.DedupStats())
    gates["dedup_exact_minhash_clean"] = exact_hit and minhash_hit and clean
    gates["script_filter"] = (not sid.passes_script_filter("abc αβγδεζ")
                              and sid.passes_script_filter("plain english text"))
    gates["latin_function_word_filter"] = (
        sid.reads_as_held_out_latin("il questo della sono anche", "pl")
        and not sid.reads_as_held_out_latin("der die und das ist nicht", "de"))
    array = np.arange(10, dtype=np.uint32)
    encoded = sid.encode_array(array)
    tampered = dict(encoded, sha256="0" * 64)
    try:
        sid.decode_array(tampered)
        gates["codec_digest_enforced"] = False
    except sid.DataContractError:
        gates["codec_digest_enforced"] = np.array_equal(sid.decode_array(encoded), array)
    bundle_path, bundle_sha = build_tiny_bundle(tmp)
    try:
        sid.load_bundle(bundle_path, "f" * 64)
        gates["bundle_digest_enforced"] = False
    except sid.DataContractError:
        gates["bundle_digest_enforced"] = True
    bundle = sid.load_bundle(bundle_path, bundle_sha)
    split = sid.split_from_bundle(bundle)
    view = sid.eval_view(bundle, ["audit"], split)
    tampered_bundle = json.loads(json.dumps(bundle["eval"]["prompts"][:1]))
    tampered_bundle[0]["cluster"] = sorted(split.primary)[0]
    try:
        sid.check_partition_read(bundle, "audit", [p["cluster"] for p in tampered_bundle])
        gates["partition_read_fails_closed"] = False
    except tsi.IndexerContractError:
        gates["partition_read_fails_closed"] = True
    tokens, q0, q1, n0, n1 = view.prompt_tokens(view.prompts[0])
    gates["prompt_layout"] = 0 <= n0 < n1 <= q0 < q1 <= len(tokens)
    reports = bundle["reports"]["dedup"]
    gates["builder_filters_counted"] = (reports["bi-en-th"]["removed_held_out_script"] >= 1
                                        and reports["bi-en-de"][
                                            "removed_held_out_latin_function_words"] >= 1)
    return {"bundle_sha256": bundle_sha, "eval_counts": bundle["eval"]["counts"],
            "gates": gates}


def case_end_to_end(tmp: Path) -> dict[str, Any]:
    from scripts.compare_sparse_indexer_resume import compare

    run = TinyRun(tmp / "e2e")
    gates: dict[str, bool] = {}
    details: dict[str, Any] = {}
    bad = run.run("smoke", tmp / "bad-digest", bundle_sha="0" * 64)
    gates["digest_mismatch_exits_2"] = bad.returncode == 2
    smoke = run.run("smoke", tmp / "smoke", workers=1)
    gates["smoke_passes"] = smoke.returncode == 0 and receipt_of(tmp / "smoke")["status"] in (
        "SMOKE_PASS", "SMOKE_PASS_OVER_BUDGET")
    details["smoke_stderr_tail"] = smoke.stderr[-800:] if smoke.returncode else ""
    headroom = run.run("headroom-dev", tmp / "headroom")
    gates["headroom_dev_completes"] = headroom.returncode == 0 and "decision" in receipt_of(
        tmp / "headroom")
    details["headroom_stderr_tail"] = headroom.stderr[-800:] if headroom.returncode else ""
    # Resume legs: R0 uninterrupted; R1 holds after step 2 and is signalled; R2 resumes.
    r0 = run.run("resume-test", tmp / "r0", "--stop-after-step", "4", "--checkpoint-every", "2")
    r1_dir = tmp / "r1"
    r1_dir.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(run.argv("resume-test", r1_dir, "--stop-after-step", "4",
                                        "--hold-after-step", "2", "--checkpoint-every", "2"),
                               env=run.env(r1_dir), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    holding = r1_dir / "phase-0a-k1" / "checkpoints" / "holding"
    deadline = time.time() + 600
    while time.time() < deadline and len(list(holding.glob("worker-*.json"))) < 2:
        if process.poll() is not None:
            break
        time.sleep(0.5)
    stale = r1_dir / "checkpoint.ready"
    stale.write_text("stale marker from a periodic checkpoint\n", encoding="utf-8")
    process.send_signal(signal.SIGUSR1)
    _, r1_err = process.communicate(timeout=600)
    marker = json.loads(stale.read_text(encoding="utf-8")) if stale.is_file() else {}
    gates["signal_save_exits_75"] = process.returncode == 75
    gates["stale_marker_replaced_after_acks"] = (
        marker.get("token") is not None and len(marker.get("acks", {})) == 2
        and {a.get("step") for a in marker["acks"].values()} == {2})
    gates["periodic_checkpoints_write_no_marker"] = not (tmp / "r0" / "checkpoint.ready").exists()
    r2_dir = tmp / "r2"
    (r2_dir / "phase-0a-k1").mkdir(parents=True, exist_ok=True)
    shutil.copytree(r1_dir / "phase-0a-k1" / "checkpoints",
                    r2_dir / "phase-0a-k1" / "checkpoints")
    r2 = run.run("resume-test", r2_dir, "--stop-after-step", "4", "--checkpoint-every", "2")
    termination = r1_dir / "termination.env"
    termination.write_text("reason=signal_USR1_checkpoint_confirmed\nexit_code=75\n"
                           "checkpoint_ready=true\n", encoding="utf-8")
    if r0.returncode == 0 and r2.returncode == 0:
        comparison = compare(tmp / "r0", r1_dir, r2_dir)
        gates["resume_bitwise_equal"] = comparison["equivalent"]
        details["resume"] = {"checks": comparison["checks"],
                             "r2_resumed_from": comparison["r2_resumed_from"]}
    else:
        gates["resume_bitwise_equal"] = False
        details["resume_stderr"] = (r0.stderr[-600:], r1_err[-600:], r2.stderr[-600:])
    main_run = run.run("0a-k1", tmp / "main")
    gates["main_completes_with_verdict"] = main_run.returncode == 0 and receipt_of(
        tmp / "main")["verdict"]["verdict"] in {
        "GO", "NEGATIVE", "INCONCLUSIVE", "UNINTERPRETABLE", "HOLD", "V1_EXTENSION_REQUIRED"}
    if main_run.returncode == 0:
        main_receipt = receipt_of(tmp / "main")
        details["main"] = {"verdict": main_receipt["verdict"],
                           "lr_freeze": main_receipt["lr_freeze"]["selected_lr"],
                           "units": main_receipt["units"]}
        gates["lr_freeze_hashed_before_audit"] = bool(
            main_receipt["hashes"].get("lr_freeze_sha256"))
        ext_dir = tmp / "extension"
        (ext_dir / "phase-0a-k1").mkdir(parents=True, exist_ok=True)
        shutil.copytree(tmp / "main" / "phase-0a-k1" / "checkpoints",
                        ext_dir / "phase-0a-k1" / "checkpoints",
                        ignore=shutil.ignore_patterns("eval"))
        extension = run.run("0a-k1-extend", ext_dir)
        gates["extension_completes"] = extension.returncode == 0 and (
            ext_dir / "phase-0a-k1" / "receipt-extension.json").is_file()
        details["extension_stderr_tail"] = extension.stderr[-800:] if extension.returncode else ""
    else:
        details["main_stderr_tail"] = main_run.stderr[-1500:]
        gates["lr_freeze_hashed_before_audit"] = False
        gates["extension_completes"] = False
    return {"gates": gates, "details": details}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-end-to-end", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists():
        raise SystemExit(f"{args.output} exists; a doctor rerun writes a new path")
    started = time.perf_counter()
    cases: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="k1-doctor-") as raw:
        tmp = Path(raw)
        cases["capture_vs_eager"] = case_capture_vs_eager(tmp)
        cases["targets_vs_numpy"] = case_targets_vs_numpy()
        cases["selection_brute_force"] = case_selection_brute_force()
        cases["gradient_check"] = case_gradient_check()
        cases["verdict_tables"] = case_verdict_tables()
        cases["data_objects"] = case_data_objects(tmp / "data")
        if not args.skip_end_to_end:
            cases["end_to_end"] = case_end_to_end(tmp)
    case_status = {name: "PASS" if all(case["gates"].values()) else "FAIL"
                   for name, case in cases.items()}
    all_pass = all(status == "PASS" for status in case_status.values())
    payload = {
        "schema_version": "1.0", "doctor": DOCTOR_NAME,
        "status": "K1_DOCTOR_PASS" if all_pass else "K1_DOCTOR_FAIL",
        "evidence_grade": EVIDENCE_GRADE, "numbers_are_synthetic": True,
        "case_status": case_status, "cases": cases,
        "runtime_seconds": time.perf_counter() - started,
        "provenance": {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
                       for name in ("harness/sparse_indexer_torch.py",
                                    "harness/sparse_indexer_k1_runtime.py",
                                    "harness/sparse_indexer_k1_stats.py",
                                    "harness/sparse_indexer_data.py",
                                    "scripts/run_sparse_indexer_phase0a.py",
                                    "scripts/build_sparse_indexer_k1_bundle.py",
                                    "scripts/run_sparse_indexer_k1_doctor.py")},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({"status": payload["status"], "case_status": case_status}))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
