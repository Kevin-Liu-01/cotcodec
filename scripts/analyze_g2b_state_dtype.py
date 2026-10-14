#!/usr/bin/env python3
"""g2b-state-dtype-v1 (EXPLORATORY): join the jobs' outputs, then mismatch and throughput tables.

CPU only. Subcommands:

* ``pack --model M --rollouts FP32_DIR BF16_DIR --prefill DIR --teacher-force DIR --output F``:
  one per-token file per model. The rollout dirs are the two arms' worker directories
  (``<model>-<arm>/`` with ``tokens.npz`` and ``sequences.json``); the prefill and
  teacher-forcing dirs hold ``prefill-<arm>.npz`` and ``tf-<model>.npz``. Token ids are checked
  equal across all jobs. Per completion token it keeps every path as an fp16 difference from the
  trainer path r1 (``d_dec``, ``d_pre32``, ``d_pre16``, ``d_r2``, ``d_r4``), the r1 and r4
  entropies (fp16), and, on the shared prefix of the two arms' rollouts of one prompt and seed,
  the decode-path difference bf16 minus fp32 (``d_pair``).
* ``throughput --rollout-jobs DIR... --output F``: engine block pools, log facts and the
  phase R and S summaries and time series of every rollout job, as one JSON.
* ``analyze --per-token F... --throughput F --output-dir D``: tables (JSON, Markdown) and the
  figure.

Mismatch: d = log p_A - log p_B on the rollout's own tokens. ``dec`` vLLM decode (the rollout),
``pre`` vLLM prefill in the arm's own state dtype, ``preo`` prefill in the other dtype,
``pre32``/``pre16`` prefill with the fp32 or bf16 state, ``r1`` HF+FLA unpacked bf16 (trainer),
``r2`` HF+FLA packed varlen bf16, ``r4`` fp32 reference. Slopes are of |d| on position per 1,000
tokens: pooled, with entropy-bin fixed effects, within sequences (sequence fixed effects), and
within sequence x entropy-bin cells (analyze_g2_pilot). Arm contrasts (bf16 minus fp32) use a
bootstrap over prompts, since both arms share the prompts.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import g2_pilot as g2  # noqa: E402
from harness import g2b_state_dtype as gb  # noqa: E402
from scripts import analyze_g2_pilot as ap  # noqa: E402

ARMS = gb.ARM_NAMES
COMPARISONS = [
    ("dec", "r1"),
    ("dec", "r2"),
    ("dec", "r4"),
    ("dec", "pre"),
    ("dec", "preo"),
    ("pre", "r1"),
    ("r2", "r1"),
    ("r1", "r4"),
    ("pre", "r4"),
    ("pre32", "pre16"),
    ("pair", "r1"),
]
LABELS = {
    "dec": "vLLM decode (rollout)",
    "pre": "vLLM prefill, same state dtype",
    "preo": "vLLM prefill, other state dtype",
    "pre32": "vLLM prefill, fp32 state",
    "pre16": "vLLM prefill, bf16 state",
    "r1": "HF+FLA unpacked bf16 (trainer)",
    "r2": "HF+FLA packed varlen bf16",
    "r4": "fp32 reference",
    "pair": "decode bf16 minus decode fp32, shared prefix",
}
#: Comparisons whose arm contrast (bf16 minus fp32) is reported.
CONTRASTS = [
    ("dec", "r1"),
    ("dec", "r2"),
    ("dec", "r4"),
    ("dec", "pre"),
    ("pre", "r1"),
    ("r1", "r4"),
]
LOG_PATTERNS = {
    "kv_cache_tokens": re.compile(r"GPU KV cache size: ([\d,]+) tokens"),
    "max_concurrency": re.compile(
        r"Maximum concurrency for ([\d,]+) tokens per request: ([\d.]+)x"
    ),
    "attention_block_tokens": re.compile(r"Setting attention block size to (\d+) tokens"),
    "mamba_padding_pct": re.compile(r"Padding mamba page size by ([\d.]+)%"),
    "gdn_decode_kernel": re.compile(r"GDN decode kernel: (\S+)"),
}


# --------------------------------------------------------------------------- pack


def _load_rollout_arm(directory: Path) -> dict[str, Any]:
    tokens = np.load(directory / "tokens.npz")
    meta = json.loads((directory / "sequences.json").read_text(encoding="utf-8"))
    order = meta["sequence_order"]
    by_id = {s["sequence_id"]: s for s in meta["sequences"]}
    return {
        "tokens": tokens,
        "order": order,
        "index": {k: i for i, k in enumerate(order)},
        "meta": by_id,
        "arm": meta["arm"],
    }


def common_prefix(a: np.ndarray, b: np.ndarray) -> int:
    n = min(len(a), len(b))
    if n == 0:
        return 0
    differ = np.nonzero(a[:n] != b[:n])[0]
    return int(differ[0]) if len(differ) else n


def pack_model(
    model_id: str, rollout_dirs: list[Path], prefill_dir: Path, tf_dir: Path
) -> dict[str, np.ndarray]:
    tf = np.load(tf_dir / f"tf-{model_id}.npz")
    tf_seqs = json.loads((tf_dir / f"tf-{model_id}-sequences.json").read_text(encoding="utf-8"))
    order = [s["sequence_id"] for s in tf_seqs]
    offsets = tf["offsets"]
    n_seq = len(order)
    arms = {}
    for directory in rollout_dirs:
        loaded = _load_rollout_arm(directory)
        arms[loaded["arm"]] = loaded
    if set(arms) != set(ARMS):
        raise ValueError(f"{model_id}: need one rollout dir per arm {ARMS}, got {sorted(arms)}")
    prefill = {}
    for arm in ARMS:
        record = json.loads((prefill_dir / f"prefill-{arm}.json").read_text(encoding="utf-8"))
        if record["sequence_order"] != order:
            raise ValueError(
                f"{model_id}: prefill {arm} sequence order differs from teacher forcing"
            )
        data = np.load(prefill_dir / f"prefill-{arm}.npz")
        if not np.array_equal(data["offsets"], offsets):
            raise ValueError(f"{model_id}: prefill {arm} offsets differ")
        prefill[arm] = data["logp_prefill"].astype(np.float64)
    total = int(offsets[-1])
    dec = np.full(total, np.nan)
    seq_arm = np.zeros(n_seq, dtype=np.int8)
    seq_seed = np.zeros(n_seq, dtype=np.int16)
    seq_prompt = np.zeros(n_seq, dtype=np.int16)
    finished = np.zeros(n_seq, dtype=np.int8)
    for i, seq_id in enumerate(order):
        parts = gb.parse_sequence_id(seq_id)
        if parts["model_id"] != model_id:
            raise ValueError(f"{seq_id}: not {model_id}")
        arm = arms[parts["arm"]]
        j = arm["index"][seq_id]
        lo, hi = arm["tokens"]["offsets"][j], arm["tokens"]["offsets"][j + 1]
        if not np.array_equal(
            arm["tokens"]["token_ids"][lo:hi], tf["token_ids"][offsets[i] : offsets[i + 1]]
        ):
            raise ValueError(f"{seq_id}: tokens differ between rollout and teacher forcing")
        dec[offsets[i] : offsets[i + 1]] = arm["tokens"]["logp_decode"][lo:hi]
        seq_arm[i] = ARMS.index(parts["arm"])
        seq_seed[i] = parts["seed"]
        seq_prompt[i] = parts["prompt_index"]
        finished[i] = 1 if arm["meta"][seq_id]["finish_reason"] == "stop" else 0
    r1 = tf["logp_r1"].astype(np.float64)
    within = np.arange(total) - np.repeat(offsets[:-1], np.diff(offsets))
    position = (np.repeat(tf["prompt_len"], np.diff(offsets)) + within).astype(np.int32)
    out: dict[str, np.ndarray] = {
        "offsets": offsets,
        "prompt_len": tf["prompt_len"],
        "arm": seq_arm,
        "seed": seq_seed,
        "prompt_index": seq_prompt,
        "finished": finished,
        "pack_id": tf["pack_id"],
        "pack_slot": tf["pack_slot"],
        "position": position,
        "logp_r1": r1.astype(np.float32),
        "ent_r1": tf["ent_r1"].astype(np.float16),
        "ent_r4": tf["ent_r4"].astype(np.float16)
        if "ent_r4" in tf
        else np.full(total, np.nan, np.float16),
    }
    sources = {"dec": dec, "pre32": prefill["fp32"], "pre16": prefill["bf16"]}
    for key in ("r2", "r4"):
        if f"logp_{key}" in tf:
            sources[key] = tf[f"logp_{key}"].astype(np.float64)
    for key, values in sources.items():
        out[f"d_{key}"] = (values - r1).astype(np.float16)
    # Shared prefix of the two arms' rollouts of one prompt and seed.
    partner = np.full(n_seq, -1, dtype=np.int32)
    prefix = np.zeros(n_seq, dtype=np.int32)
    pair = np.full(total, np.nan)
    key_of = {(int(seq_arm[i]), int(seq_prompt[i]), int(seq_seed[i])): i for i in range(n_seq)}
    for i in range(n_seq):
        j = key_of.get((1 - int(seq_arm[i]), int(seq_prompt[i]), int(seq_seed[i])))
        if j is None:
            continue
        partner[i] = j
        a = tf["token_ids"][offsets[i] : offsets[i + 1]]
        b = tf["token_ids"][offsets[j] : offsets[j + 1]]
        prefix[i] = common_prefix(a, b)
        if seq_arm[i] == 1 and prefix[i] > 0:
            n = prefix[i]
            pair[offsets[i] : offsets[i] + n] = (
                dec[offsets[i] : offsets[i] + n] - dec[offsets[j] : offsets[j] + n]
            )
    out["partner"] = partner
    out["common_prefix"] = prefix
    out["d_pair"] = (pair - 0.0).astype(np.float16)
    return out


def pack_main(args: argparse.Namespace) -> int:
    packed = pack_model(
        args.model, [Path(p) for p in args.rollouts], Path(args.prefill), Path(args.teacher_force)
    )
    meta = {
        "experiment_id": gb.EXPERIMENT_ID,
        "model": args.model,
        "sequences": int(len(packed["prompt_len"])),
        "tokens": int(packed["offsets"][-1]),
        "d_pair_is": "decode bf16 minus decode fp32 on the shared prefix (bf16-arm tokens)",
    }
    packed["meta_json"] = np.frombuffer(json.dumps(meta, sort_keys=True).encode(), dtype=np.uint8)
    np.savez_compressed(args.output, **packed)
    print(json.dumps(meta, sort_keys=True))
    return 0


def load_per_token(path: Path) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    raw = np.load(path)
    meta = json.loads(bytes(raw["meta_json"]).decode())
    return meta, {k: raw[k] for k in raw.files if k != "meta_json"}


# --------------------------------------------------------------------------- statistics


def analysis_data(raw: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """The per-token arrays in the form analyze_g2_pilot.comparison_block reads: every path as a
    difference from r1 around a zero anchor, plus the same- and other-dtype prefill."""

    offsets = raw["offsets"]
    seq = np.repeat(np.arange(len(offsets) - 1), np.diff(offsets))
    arm_token = raw["arm"][seq]
    data: dict[str, np.ndarray] = {
        "offsets": offsets,
        "position": raw["position"],
        "logp_r1": np.zeros(int(offsets[-1])),
        "ent_r1": raw["ent_r1"].astype(np.float64),
        "seq": seq,
        "arm_token": arm_token,
        "seed_token": raw["seed"][seq],
    }
    for key in ("dec", "pre32", "pre16", "r2", "r4", "pair"):
        if f"d_{key}" in raw:
            data[f"d_{key}"] = raw[f"d_{key}"].astype(np.float64)
    if "d_pre32" in data and "d_pre16" in data:
        data["d_pre"] = np.where(arm_token == 0, data["d_pre32"], data["d_pre16"])
        data["d_preo"] = np.where(arm_token == 0, data["d_pre16"], data["d_pre32"])
    return data


def sequence_stats(
    data: dict[str, np.ndarray], a_key: str, b_key: str, mask: np.ndarray, edges: list[float]
) -> np.ndarray:
    """Per sequence: [n, sum |d|, cxy, cxx (sequence FE), cxy, cxx (sequence x entropy FE),
    sum k3]; k3 only when a is the decode path. x is position / 1000, y is |d|."""

    a = ap.path_logp(data, a_key)
    b = ap.path_logp(data, b_key)
    n_seq = len(data["offsets"]) - 1
    out = np.zeros((n_seq, 7))
    if a is None or b is None:
        return out
    valid = mask & np.isfinite(a) & np.isfinite(b)
    seq = data["seq"][valid]
    x = data["position"][valid].astype(np.float64) / 1000.0
    d = a[valid] - b[valid]
    y = np.abs(d)
    groups = ap.entropy_groups(data["ent_r1"][valid], edges)
    out[:, 0] = np.bincount(seq, minlength=n_seq)
    out[:, 1] = np.bincount(seq, weights=y, minlength=n_seq)
    for col, cells in ((2, None), (4, groups)):
        n_cells = int(cells.max()) + 1 if cells is not None and len(cells) else 1
        key = seq.astype(np.int64) * n_cells + (cells if cells is not None else 0)
        size = n_seq * n_cells
        n = np.bincount(key, minlength=size).astype(float)
        sx = np.bincount(key, weights=x, minlength=size)
        sy = np.bincount(key, weights=y, minlength=size)
        sxy = np.bincount(key, weights=x * y, minlength=size)
        sxx = np.bincount(key, weights=x * x, minlength=size)
        safe = np.where(n > 0, n, 1.0)
        out[:, col] = np.where(n > 0, sxy - sx * sy / safe, 0.0).reshape(n_seq, n_cells).sum(1)
        out[:, col + 1] = np.where(n > 0, sxx - sx * sx / safe, 0.0).reshape(n_seq, n_cells).sum(1)
    if a_key == "dec":
        r = -d  # log p_B - log p_dec
        out[:, 6] = np.bincount(seq, weights=np.expm1(r) - r, minlength=n_seq)
    return out


def arm_contrast(
    stats: np.ndarray, seq_arm: np.ndarray, seq_prompt: np.ndarray, reps: int, seed: int
) -> dict[str, Any]:
    """bf16 minus fp32 in mean |d|, k3 and the within-sequence slopes, with a 95% bootstrap over
    prompts (each draw takes a prompt's sequences in both arms)."""

    present = stats[:, 0] > 0
    prompts = sorted(
        set(seq_prompt[present & (seq_arm == 0)]) & set(seq_prompt[present & (seq_arm == 1)])
    )
    if len(prompts) < 3:
        return {"prompts": len(prompts)}
    index = {p: k for k, p in enumerate(prompts)}
    per = np.zeros((2, len(prompts), stats.shape[1]))
    for i in np.nonzero(present)[0]:
        k = index.get(int(seq_prompt[i]))
        if k is not None:
            per[int(seq_arm[i]), k] += stats[i]

    def measures(sums: np.ndarray) -> dict[str, np.ndarray]:
        n = sums[..., 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            return {
                "mean_abs": sums[..., 1] / n,
                "k3": sums[..., 6] / n,
                "slope_within_sequences_per_1k": sums[..., 2] / sums[..., 3],
                "slope_within_sequence_entropy_cells_per_1k": sums[..., 4] / sums[..., 5],
            }

    point = {arm: measures(per[i].sum(0)) for i, arm in enumerate(ARMS)}
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(prompts), size=(reps, len(prompts)))
    counts = np.stack([np.bincount(row, minlength=len(prompts)) for row in draws]).astype(float)
    boot = {arm: measures(counts @ per[i]) for i, arm in enumerate(ARMS)}
    out: dict[str, Any] = {
        "prompts": len(prompts),
        "sequences": {arm: int((present & (seq_arm == i)).sum()) for i, arm in enumerate(ARMS)},
    }
    for name in point["fp32"]:
        f, b = float(point["fp32"][name]), float(point["bf16"][name])
        diff = boot["bf16"][name] - boot["fp32"][name]
        diff = diff[np.isfinite(diff)]
        record: dict[str, Any] = {"fp32": f, "bf16": b, "diff": b - f}
        if len(diff):
            record["diff_ci95"] = [
                float(np.percentile(diff, 2.5)),
                float(np.percentile(diff, 97.5)),
            ]
        if name in ("mean_abs", "k3") and f > 0:
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = boot["bf16"][name] / boot["fp32"][name]
            ratio = ratio[np.isfinite(ratio)]
            record["ratio"] = b / f
            if len(ratio):
                record["ratio_ci95"] = [
                    float(np.percentile(ratio, 2.5)),
                    float(np.percentile(ratio, 97.5)),
                ]
        out[name] = record
    return out


def position_contrast(
    data: dict[str, np.ndarray],
    a_key: str,
    b_key: str,
    seq_prompt: np.ndarray,
    width: int,
    reps: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Per position bin: each arm's mean |d|, sequences, and the bf16/fp32 ratio with a 95%
    bootstrap over prompts."""

    a = ap.path_logp(data, a_key)
    b = ap.path_logp(data, b_key)
    if a is None or b is None:
        return []
    valid = np.isfinite(a) & np.isfinite(b)
    bins = data["position"] // width
    prompts = sorted(set(seq_prompt.tolist()))
    index = {p: k for k, p in enumerate(prompts)}
    tok_prompt = np.asarray([index[int(p)] for p in seq_prompt])[data["seq"]]
    absd = np.abs(a - b)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(prompts), size=(reps, len(prompts)))
    counts = np.stack([np.bincount(row, minlength=len(prompts)) for row in draws]).astype(float)
    rows = []
    for index_bin in np.unique(bins[valid]):
        row: dict[str, Any] = {"start": int(index_bin * width)}
        sums = {}
        for arm_index, arm in enumerate(ARMS):
            m = valid & (bins == index_bin) & (data["arm_token"] == arm_index)
            row[f"{arm}_tokens"] = int(m.sum())
            row[f"{arm}_sequences"] = int(len(np.unique(data["seq"][m])))
            row[f"{arm}_mean_abs"] = float(absd[m].mean()) if m.any() else float("nan")
            sums[arm] = (
                np.bincount(tok_prompt[m], minlength=len(prompts)).astype(float),
                np.bincount(tok_prompt[m], weights=absd[m], minlength=len(prompts)),
            )
        if row["fp32_tokens"] and row["bf16_tokens"]:
            row["ratio"] = row["bf16_mean_abs"] / row["fp32_mean_abs"]
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = (counts @ sums["bf16"][1] / (counts @ sums["bf16"][0])) / (
                    counts @ sums["fp32"][1] / (counts @ sums["fp32"][0])
                )
            ratio = ratio[np.isfinite(ratio)]
            if len(ratio) > reps // 2:
                row["ratio_ci95"] = [
                    float(np.percentile(ratio, 2.5)),
                    float(np.percentile(ratio, 97.5)),
                ]
        rows.append(row)
    return rows


def analyze_model(raw: dict[str, np.ndarray], settings: dict[str, Any]) -> dict[str, Any]:
    data = analysis_data(raw)
    edges = g2.numeric_edges(settings["entropy_edges"], "entropy_edges")
    reps, seed = int(settings["bootstrap_reps"]), int(settings["bootstrap_seed"])
    offsets = raw["offsets"]
    lengths = np.diff(offsets)
    seq_arm, seq_prompt, seq_seed = raw["arm"], raw["prompt_index"], raw["seed"]
    result: dict[str, Any] = {"arms": {}, "subsets": {}, "contrasts": {}, "position_contrast": {}}
    for i, arm in enumerate(ARMS):
        m = seq_arm == i
        ends = raw["position"][offsets[1:][m] - 1] + 1 if m.any() else np.asarray([0])
        result["arms"][arm] = {
            "sequences": int(m.sum()),
            "tokens": int(lengths[m].sum()),
            "finished": int(raw["finished"][m].sum()),
            "completion_len": {
                "median": float(np.median(lengths[m])),
                "max": int(lengths[m].max()),
                "min": int(lengths[m].min()),
            },
            "sequences_reaching": {
                str(k): int((ends >= k).sum()) for k in (8192, 16384, 24576, 32768)
            },
        }
    subsets: dict[str, np.ndarray] = {}
    for i, arm in enumerate(ARMS):
        subsets[f"{arm}/all"] = data["arm_token"] == i
        for s in sorted(set(seq_seed.tolist())):
            subsets[f"{arm}/seed_{s}"] = (data["arm_token"] == i) & (data["seed_token"] == s)
    subsets["both/all"] = np.ones(len(data["seq"]), dtype=bool)
    for name, mask in subsets.items():
        blocks = {}
        for a_key, b_key in COMPARISONS:
            if name.startswith("both") and (a_key, b_key) not in (
                ("pre32", "pre16"),
                ("r2", "r1"),
                ("r1", "r4"),
            ):
                continue
            if "seed_" in name and (a_key, b_key) not in (
                ("dec", "r1"),
                ("dec", "pre"),
                ("pre32", "pre16"),
            ):
                continue
            block = ap.comparison_block(data, a_key, b_key, mask, settings)
            if block is not None:
                blocks[f"{a_key}_vs_{b_key}"] = block
        result["subsets"][name] = blocks
    for a_key, b_key in CONTRASTS:
        stats = sequence_stats(data, a_key, b_key, np.ones(len(data["seq"]), dtype=bool), edges)
        result["contrasts"][f"{a_key}_vs_{b_key}"] = arm_contrast(
            stats, seq_arm, seq_prompt, reps, seed
        )
    for a_key, b_key in (("dec", "r1"), ("dec", "pre")):
        result["position_contrast"][f"{a_key}_vs_{b_key}"] = position_contrast(
            data, a_key, b_key, seq_prompt, int(settings["position_bin"]), reps, seed
        )
    prefix = raw["common_prefix"][seq_arm == 1]
    result["shared_prefix"] = {
        "pairs": int((raw["partner"][seq_arm == 1] >= 0).sum()),
        "median": float(np.median(prefix)) if len(prefix) else None,
        "quartiles": [float(np.percentile(prefix, q)) for q in (25, 75)] if len(prefix) else None,
        "max": int(prefix.max()) if len(prefix) else None,
        "lengths": [int(v) for v in prefix],
    }
    packs = raw["pack_id"][raw["pack_id"] >= 0]
    result["packs"] = {
        "packs": int(len(np.unique(packs))),
        "sequences": int(len(packs)),
        "max_slot": int(raw["pack_slot"].max()),
    }
    # Packed path by slot in pack (a leak across sequences would grow with the slot).
    by_slot = []
    for slot in sorted(set(raw["pack_slot"][raw["pack_slot"] >= 0].tolist())):
        mask = (raw["pack_slot"] == slot)[data["seq"]]
        block = ap.comparison_block(data, "r2", "r1", mask, settings)
        if block is not None:
            by_slot.append(
                {
                    "slot": slot,
                    "sequences": block["sequences"],
                    "tokens": block["tokens"],
                    "mean_abs": block["mean_abs"],
                    "p99_abs": block["p99_abs"],
                }
            )
    result["packed_by_slot"] = by_slot
    return result


# --------------------------------------------------------------------------- throughput


def _number(text: str) -> Any:
    try:
        return float(text)
    except ValueError:
        return text


def parse_log(path: Path) -> dict[str, Any]:
    facts: dict[str, Any] = {"lines": []}
    if not path.is_file():
        return facts
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        for key, pattern in LOG_PATTERNS.items():
            match = pattern.search(line)
            if match and key not in facts:
                groups = [_number(g.replace(",", "")) for g in match.groups()]
                facts[key] = groups if len(groups) > 1 else groups[0]
        lowered = line.lower()
        if (
            any(s in lowered for s in ("gdn", "mamba", "kv cache size", "maximum concurrency"))
            and len(facts["lines"]) < 40
        ):
            facts["lines"].append(re.sub(r"^.*?\] ", "", line)[:300])
    return facts


def series(stats_path: Path, step_s: float) -> dict[str, list[float]]:
    """Output tokens per second and metric samples, on a coarse time grid, for the figure."""

    out: dict[str, list[float]] = {}
    if stats_path.is_file():
        st = np.load(stats_path)
        if len(st["t"]):
            edges = np.arange(0.0, float(st["t"].max()) + step_s, step_s)
            tok, _ = np.histogram(st["t"], bins=edges, weights=st["tokens"])
            out["t"] = [round(float(x), 2) for x in edges[1:]]
            out["tok_per_s"] = [round(float(x) / step_s, 1) for x in tok]
    metrics = stats_path.with_suffix(".metrics.jsonl")
    if metrics.is_file():
        rows = [
            json.loads(line) for line in metrics.read_text(encoding="utf-8").splitlines() if line
        ]
        for key in ("running", "waiting", "kv_usage", "preemptions"):
            out[f"metric_{key}"] = [round(float(r.get(key, float("nan"))), 4) for r in rows]
        out["metric_t"] = [float(r["t"]) for r in rows]
    return out


def throughput_job(job_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    summary = json.loads((job_dir / "summary.json").read_text(encoding="utf-8"))
    model_id, arm = summary["model"], summary["arm"]
    worker = job_dir / f"{model_id}-{arm}"
    wsum = (
        json.loads((worker / "summary.json").read_text(encoding="utf-8"))
        if (worker / "summary.json").is_file()
        else {}
    )
    engine = wsum.get("engine") or json.loads((worker / "engine.json").read_text(encoding="utf-8"))
    log = parse_log(job_dir / f"worker-{model_id}-{arm}.log")
    resolved = gb.resolved_state_dtype(summary["state_dtype"])
    record: dict[str, Any] = {
        "job_dir": job_dir.name,
        "model": model_id,
        "arm": arm,
        "state_dtype_setting": summary["state_dtype"],
        "engine": engine,
        "log": log,
        "smoke": summary.get("smoke"),
        "phases": wsum.get("phases", {}),
    }
    gdn_layers = config["models"][model_id]["gdn_layers"]
    record["gdn_state_mib_per_sequence"] = gb.gdn_page_bytes(config, resolved) * gdn_layers / 2**20
    block = log.get("attention_block_tokens") or engine.get("block_size")
    blocks = engine.get("num_gpu_blocks")
    if block and blocks:
        block, blocks = int(block), int(blocks)
        record["block_tokens"] = block
        record["max_sequences_by_length"] = {
            str(n): gb.max_sequences(blocks, n, block)
            for n in config["analysis"]["concurrency_lengths"]
        }
    phases = {}
    for name in record["phases"]:
        phases[name] = series(
            worker / f"phase-{name}-stats.npz", 1.0 if name.startswith("S") else 5.0
        )
    record["series"] = phases
    return record


def throughput_main(args: argparse.Namespace) -> int:
    config = gb.load_config()
    jobs = [throughput_job(Path(d), config) for d in args.rollout_jobs]
    g2.write_json(Path(args.output), {"experiment_id": gb.EXPERIMENT_ID, "jobs": jobs})
    print(json.dumps({"jobs": [f"{j['model']}/{j['arm']}" for j in jobs]}))
    return 0


def saturation_table(jobs: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    """Per model: each arm's waves, their spread, and the bf16/fp32 ratio per seed."""

    out: dict[str, Any] = {}
    for model_id in config["models"]:
        per_arm = {j["arm"]: j for j in jobs if j["model"] == model_id and not j.get("smoke")}
        if not per_arm:
            continue
        model: dict[str, Any] = {}
        for arm, job in per_arm.items():
            waves = {
                k: v
                for k, v in job["phases"].items()
                if k.startswith("S") and v.get("status") != "skipped"
            }
            model[arm] = {
                "waves": {
                    k: {
                        key: v.get(key)
                        for key in (
                            "wall_s",
                            "output_tok_per_s",
                            "peak_running",
                            "mean_running",
                            "peak_waiting",
                            "peak_kv_usage",
                            "preemptions_delta",
                            "complete",
                        )
                    }
                    for k, v in waves.items()
                },
                "output_tok_per_s": gb.spread([v.get("output_tok_per_s") for v in waves.values()]),
                "wall_s": gb.spread([v.get("wall_s") for v in waves.values()]),
                "peak_running": gb.spread([v.get("peak_running") for v in waves.values()]),
                "preemptions": gb.spread([v.get("preemptions_delta") for v in waves.values()]),
            }
        if set(model) == set(ARMS):
            ratios = []
            for name, wave in model["bf16"]["waves"].items():
                other = model["fp32"]["waves"].get(name)
                if other and other.get("output_tok_per_s") and wave.get("output_tok_per_s"):
                    ratios.append(wave["output_tok_per_s"] / other["output_tok_per_s"])
            model["bf16_over_fp32_tok_per_s"] = gb.spread(ratios) | {"per_seed": ratios}
        out[model_id] = model
    return out


# --------------------------------------------------------------------------- report


def fmt(value: Any, digits: int = 4) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "n/a"
    if isinstance(value, int):
        return f"{value:,}"
    if value != 0 and abs(value) < 10 ** (-digits):
        return f"{value:.2e}"
    return f"{value:.{digits}f}"


def sci(value: Any) -> str:
    if value is None or not math.isfinite(float(value)):
        return "n/a"
    return f"{float(value):+.2e}"


def ci(pair: Any, f: Any = sci) -> str:
    if not pair:
        return ""
    return f" [{f(pair[0])}, {f(pair[1])}]"


def markdown(result: dict[str, Any]) -> str:
    lines = ["# g2b-state-dtype-v1 tables (EXPLORATORY)", ""]
    lines.append(
        "d = log p_A - log p_B per completion token on the rollout's own tokens. Slopes: |d| on "
        "position per 1,000 tokens, 95% bootstrap over sequences; arm contrasts: bf16 minus fp32 "
        "with a 95% bootstrap over prompts. Entropy: the r1 distribution's, in nats."
    )
    lines.append("")
    for model_id, model in result["mismatch"].items():
        lines.append(f"## {model_id}: rollouts")
        lines.append("")
        lines.append(
            "| arm | sequences | tokens | finished (EOS) | median length | max length | reaching 8K / 16K / 24K / 32K |"  # noqa: E501
        )
        lines.append("|---|---:|---:|---:|---:|---:|---|")
        for arm, a in model["arms"].items():
            reach = " / ".join(
                str(a["sequences_reaching"][k]) for k in ("8192", "16384", "24576", "32768")
            )
            lines.append(
                f"| {arm} | {a['sequences']} | {a['tokens']:,} | {a['finished']} | "
                f"{a['completion_len']['median']:.0f} | {a['completion_len']['max']:,} | {reach} |"
            )
        lines.append("")
        lines.append(f"## {model_id}: arm contrasts (bf16 minus fp32), all seeds")
        lines.append("")
        lines.append(
            "| comparison | prompts | mean abs fp32 | mean abs bf16 | ratio [95% CI] | k3 fp32 | k3 bf16 | "  # noqa: E501
            "within-sequence slope fp32 | bf16 | difference [95% CI] | within seq x entropy: difference [95% CI] |"  # noqa: E501
        )
        lines.append("|---|---:|---:|---:|---|---:|---:|---|---|---|---|")
        for name, c in model["contrasts"].items():
            if "mean_abs" not in c:
                continue
            m, k, s, se = (
                c["mean_abs"],
                c["k3"],
                c["slope_within_sequences_per_1k"],
                c["slope_within_sequence_entropy_cells_per_1k"],
            )
            lines.append(
                f"| {name} | {c['prompts']} | {fmt(m['fp32'])} | {fmt(m['bf16'])} | "
                f"{fmt(m.get('ratio'), 3)}{ci(m.get('ratio_ci95'), lambda v: fmt(v, 3))} | "
                f"{fmt(k['fp32'], 6) if name.startswith('dec') else ''} | "
                f"{fmt(k['bf16'], 6) if name.startswith('dec') else ''} | {sci(s['fp32'])} | "
                f"{sci(s['bf16'])} | {sci(s['diff'])}{ci(s.get('diff_ci95'))} | "
                f"{sci(se['diff'])}{ci(se.get('diff_ci95'))} |"
            )
        lines.append("")
        for subset, blocks in model["subsets"].items():
            lines.append(f"### {model_id}, {subset}")
            lines.append("")
            lines.append(
                "| comparison | tokens | seqs | mean abs | p99 abs | k3 | share ratio outside band | "  # noqa: E501
                "slope pooled | within entropy bins | within sequences | within sequence x entropy |"  # noqa: E501
            )
            lines.append("|---|---:|---:|---:|---:|---:|---:|---|---|---|---|")
            for name, b in blocks.items():
                lines.append(
                    f"| {name} | {b['tokens']:,} | {b['sequences']} | {fmt(b['mean_abs'])} | "
                    f"{fmt(b['p99_abs'])} | {fmt(b.get('k3'), 6)} | {fmt(b.get('share_ratio_outside_band'), 5)} | "  # noqa: E501
                    f"{ap.slope_cell(b, 'slope')} | {ap.slope_cell(b, 'slope_within_entropy_bins')} | "  # noqa: E501
                    f"{ap.slope_cell(b, 'slope_within_sequences')} | "
                    f"{ap.slope_cell(b, 'slope_within_sequence_entropy_cells')} |"
                )
            lines.append("")
        for name, rows in model["position_contrast"].items():
            lines.append(f"### {model_id}, {name} by position (1K bins), both arms")
            lines.append("")
            lines.append(
                "| bin start | fp32 seqs | fp32 mean abs | bf16 seqs | bf16 mean abs | ratio bf16/fp32 [95% CI, prompts] |"  # noqa: E501
            )
            lines.append("|---:|---:|---:|---:|---:|---|")
            for r in rows:
                lines.append(
                    f"| {r['start']:,} | {r['fp32_sequences']} | {fmt(r['fp32_mean_abs'])} | "
                    f"{r['bf16_sequences']} | {fmt(r['bf16_mean_abs'])} | "
                    f"{fmt(r.get('ratio'), 3)}{ci(r.get('ratio_ci95'), lambda v: fmt(v, 3))} |"
                )
            lines.append("")
        for arm in ARMS:
            block = model["subsets"].get(f"{arm}/all", {}).get("dec_vs_r1")
            if not block:
                continue
            lines.append(f"### {model_id}, {arm}, dec_vs_r1 by r1 entropy (float edges)")
            lines.append("")
            lines.append(
                "| entropy bin (nats) | tokens | seqs | mean abs | p99 abs | mean position | slope per 1K [95% CI] |"  # noqa: E501
            )
            lines.append("|---|---:|---:|---:|---:|---:|---|")
            for r in block["by_entropy"]:
                lines.append(
                    f"| {ap.entropy_label(r['entropy_lo'], r['entropy_hi'])} | {r['tokens']:,} | "
                    f"{r['sequences']} | {fmt(r['mean_abs'], 5)} | {fmt(r['p99_abs'])} | "
                    f"{r['mean_position']:.0f} | {sci(r['slope_per_1k'])}{ci(r['slope_ci95'])} |"
                )
            lines.append("")
        sp = model["shared_prefix"]
        lines.append(
            f"Shared prefix of the two arms' rollouts (same prompt and seed): {sp['pairs']} pairs, "
            f"median {sp['median']} tokens, quartiles {sp['quartiles']}, max {sp['max']}."
        )
        lines.append("")
        lines.append(
            f"Packed path: {model['packs']}; r2 vs r1 by slot in pack: {model['packed_by_slot']}"
        )
        lines.append("")
    sat = result.get("saturation", {})
    if sat:
        lines.append(
            "## Saturation waves (phase S): output tokens per second, mean of waves [min, max]"
        )
        lines.append("")
        lines.append(
            "| model | arm | waves | tok/s mean [min, max] | range/mean | peak running | preemptions per wave | bf16/fp32 per seed |"  # noqa: E501
        )
        lines.append("|---|---|---:|---|---:|---|---|---|")
        for model_id, model in sat.items():
            for arm in ARMS:
                if arm not in model:
                    continue
                t = model[arm]["output_tok_per_s"]
                pr = model[arm]["peak_running"]
                pe = model[arm]["preemptions"]
                ratio = model.get("bf16_over_fp32_tok_per_s", {}) if arm == "bf16" else {}
                lines.append(
                    f"| {model_id} | {arm} | {t.get('n', 0)} | {fmt(t.get('mean'), 0)} [{fmt(t.get('min'), 0)}, "  # noqa: E501
                    f"{fmt(t.get('max'), 0)}] | {fmt(t.get('range_over_mean'), 3)} | "
                    f"{fmt(pr.get('min'), 0)}-{fmt(pr.get('max'), 0)} | {fmt(pe.get('min'), 0)}-{fmt(pe.get('max'), 0)} | "  # noqa: E501
                    f"{', '.join(f'{x:.3f}' for x in ratio.get('per_seed', []))} |"
                )
        lines.append("")
    jobs = result.get("throughput_jobs", [])
    if jobs:
        lines.append("## Engines: block pool and phase R")
        lines.append("")
        lines.append(
            "| model | arm | GDN state MiB/seq | blocks | block tokens | KV tokens (log) | max seqs at 1K/2K/4K/8K/16K/32K | "  # noqa: E501
            "R tok/s | R peak running | R preemptions | R peak KV | R finished/requests |"
        )
        lines.append("|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|")
        for j in jobs:
            r = j["phases"].get("R", {})
            ms = j.get("max_sequences_by_length", {})
            lines.append(
                f"| {j['model']} | {j['arm']} | {j['gdn_state_mib_per_sequence']:.1f} | "
                f"{fmt(j['engine'].get('num_gpu_blocks'))} | {fmt(j.get('block_tokens'))} | "
                f"{fmt(j['log'].get('kv_cache_tokens'), 0)} | {' / '.join(str(v) for v in ms.values())} | "  # noqa: E501
                f"{fmt(r.get('output_tok_per_s'), 0)} | {fmt(r.get('peak_running'), 0)} | "
                f"{fmt(r.get('preemptions_delta'), 0)} | {fmt(r.get('peak_kv_usage'), 3)} | "
                f"{r.get('finished')}/{r.get('requests')} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def plot(result: dict[str, Any], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"fp32": "#1f77b4", "bf16": "#d62728"}
    fig, axes = plt.subplots(2, 3, figsize=(17, 9.5), gridspec_kw={"hspace": 0.38, "wspace": 0.26})
    models = list(result["mismatch"])
    for col, model_id in enumerate(models[:2]):
        ax = axes[0, col]
        for arm in ARMS:
            block = result["mismatch"][model_id]["subsets"].get(f"{arm}/all", {}).get("dec_vs_r1")
            if not block:
                continue
            rows = [r for r in block["by_position"] if r["tokens"] >= 200]
            x = [r["start"] / 1000 + 0.5 for r in rows]
            ax.plot(
                x,
                [r["mean_abs"] for r in rows],
                "-o",
                ms=3,
                color=colors[arm],
                label=f"{arm} state: rollout vs trainer (dec vs r1)",
            )
            ax.fill_between(
                x,
                [r["mean_abs_ci95"][0] for r in rows],
                [r["mean_abs_ci95"][1] for r in rows],
                color=colors[arm],
                alpha=0.15,
                lw=0,
            )
            ax.plot(
                x,
                [r["mean_abs_entropy_standardized"] for r in rows],
                ":",
                color=colors[arm],
                label=f"{arm}, entropy-standardized",
            )
        ax.set_title(f"{model_id}: rollout vs trainer by position (all seeds)", fontsize=9)
        ax.set_xlabel("absolute token position (K), 1K bins")
        ax.set_ylabel("mean |Δ log p| per token")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
    ax = axes[0, 2]
    styles = {"pre_vs_r1": "-", "r2_vs_r1": "--", "pre32_vs_pre16": ":"}
    for model_id, marker in zip(models[:2], ["o", "s"], strict=False):
        subsets = result["mismatch"][model_id]["subsets"]
        for name, style in styles.items():
            block = subsets.get("both/all", {}).get(name) or subsets.get("fp32/all", {}).get(name)
            if not block:
                continue
            rows = [r for r in block["by_position"] if r["tokens"] >= 200]
            ax.plot(
                [r["start"] / 1000 + 0.5 for r in rows],
                [r["mean_abs"] for r in rows],
                style,
                marker=marker,
                ms=2.5,
                label=f"{model_id} {name}",
            )
    ax.set_yscale("log")
    ax.set_title(
        "other paths: prefill vs trainer, packed vs unpacked, prefill fp32 vs bf16 state",
        fontsize=9,
    )
    ax.set_xlabel("absolute token position (K), 1K bins")
    ax.set_ylabel("mean |Δ log p| per token")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=6)
    sat = result.get("saturation", {})
    ax = axes[1, 0]
    names = [m for m in sat if all(a in sat[m] for a in ARMS)]
    for k, model_id in enumerate(names):
        for arm_index, arm in enumerate(ARMS):
            waves = [
                w["output_tok_per_s"]
                for w in sat[model_id][arm]["waves"].values()
                if w.get("output_tok_per_s")
            ]
            xpos = k + (arm_index - 0.5) * 0.35
            ax.bar(
                xpos,
                np.mean(waves) if waves else 0,
                width=0.33,
                color=colors[arm],
                alpha=0.6,
                label=arm if k == 0 else None,
            )
            ax.plot([xpos] * len(waves), waves, "k.", ms=4)
    ax.set_xticks(range(len(names)), names, fontsize=8)
    ax.set_ylabel("output tokens per second")
    ax.set_title("saturation waves (phase S), dots: one wave per seed", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(True, axis="y", alpha=0.3)
    ax = axes[1, 1]
    for k, model_id in enumerate(names):
        for arm_index, arm in enumerate(ARMS):
            peaks = [
                w["peak_running"]
                for w in sat[model_id][arm]["waves"].values()
                if w.get("peak_running") is not None
            ]
            xpos = k + (arm_index - 0.5) * 0.35
            ax.bar(
                xpos,
                max(peaks) if peaks else 0,
                width=0.33,
                color=colors[arm],
                alpha=0.6,
                label=arm if k == 0 else None,
            )
    ax.set_xticks(range(len(names)), names, fontsize=8)
    ax.set_ylabel("peak running sequences (vLLM gauge)")
    ax.set_title("concurrency reached in phase S", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(True, axis="y", alpha=0.3)
    ax = axes[1, 2]
    for job in result.get("throughput_jobs", []):
        s = job["series"].get("S42", {})
        if "metric_t" not in s:
            continue
        ax.plot(
            s["metric_t"],
            s["metric_running"],
            "-" if job["arm"] == "bf16" else "--",
            color={"qwen3.5-4b": "#2ca02c", "qwen3.5-9b": "#9467bd"}.get(job["model"], "#8c564b"),
            lw=1,
            label=f"{job['model']} {job['arm']}",
        )
    ax.set_xlabel("seconds into the seed-42 wave")
    ax.set_ylabel("running sequences")
    ax.set_title("running sequences during one saturation wave", fontsize=9)
    ax.legend(fontsize=6)
    ax.grid(True, alpha=0.3)
    fig.suptitle(
        "g2b-state-dtype-v1 (EXPLORATORY): GDN state fp32 vs bf16 in vLLM 0.31.0; bands: 95% "
        "bootstrap over sequences",
        fontsize=10,
    )
    fig.savefig(output, dpi=120, bbox_inches="tight")
    plt.close(fig)


def analyze_main(args: argparse.Namespace) -> int:
    config = gb.load_config()
    settings = dict(config["analysis"])
    result: dict[str, Any] = {
        "experiment_id": gb.EXPERIMENT_ID,
        "claim_level": "exploratory",
        "settings": settings,
        "mismatch": {},
    }
    for path in args.per_token:
        meta, raw = load_per_token(Path(path))
        result["mismatch"][meta["model"]] = analyze_model(raw, settings) | {"meta": meta}
    if args.throughput:
        jobs = json.loads(Path(args.throughput).read_text(encoding="utf-8"))["jobs"]
        result["throughput_jobs"] = jobs
        result["saturation"] = saturation_table(jobs, config)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    g2.write_json(out / "analysis.json", result)
    (out / "tables.md").write_text(markdown(result), encoding="utf-8")
    plot(result, out / "g2b-state-dtype.png")
    print(json.dumps({"written": ["analysis.json", "tables.md", "g2b-state-dtype.png"]}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack", allow_abbrev=False)
    pack.add_argument("--model", required=True)
    pack.add_argument("--rollouts", nargs=2, required=True)
    pack.add_argument("--prefill", required=True)
    pack.add_argument("--teacher-force", required=True)
    pack.add_argument("--output", required=True)
    thr = sub.add_parser("throughput", allow_abbrev=False)
    thr.add_argument("--rollout-jobs", nargs="+", required=True)
    thr.add_argument("--output", required=True)
    an = sub.add_parser("analyze", allow_abbrev=False)
    an.add_argument("--per-token", nargs="*", default=[])
    an.add_argument("--throughput", default=None)
    an.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    return {"pack": pack_main, "throughput": throughput_main, "analyze": analyze_main}[
        args.command
    ](args)


if __name__ == "__main__":
    sys.exit(main())
