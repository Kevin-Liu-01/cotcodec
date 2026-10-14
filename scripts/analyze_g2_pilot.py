#!/usr/bin/env python3
"""G2 exploratory pilot: join the rollout and teacher-forcing outputs and bin the mismatch.

EXPLORATORY (experiments/g2/g2-pilot-v1.yaml). CPU only.

Subcommands:

* ``pack --rollouts DIR --teacher-force DIR --output FILE``: join the two jobs' raw outputs
  (``<model>/tokens.npz`` and ``<model>/sequences.json`` from the rollout job,
  ``tf-<model>.npz`` and ``tf-<model>-sequences.json`` from the teacher-forcing job) into one
  compact per-token file: for each completion token its absolute position, the r1 (trainer
  bf16) log-prob in fp32 as the anchor, every other path as an fp16 difference from it, and
  the r1 and r4 entropies in fp16. Token ids are checked equal across the two jobs.
* ``analyze --per-token FILE --output-dir DIR``: tables (JSON and Markdown) and the figure.

Comparisons (d = log p_A - log p_B on the rollout's own tokens):
``dec`` vLLM decode (the rollout), ``pre`` vLLM prefill recompute (R5), ``r1`` HF+FLA chunk
bf16, ``r3`` HF+FLA fused_recurrent bf16, ``r4`` fp32 reference. For comparisons with ``dec``
the tokens are samples from the decode distribution, so mean k3 with log-ratio
``log p_B - log p_A`` estimates KL(p_dec || p_B), and the importance ratio is
``exp(log p_B - log p_dec)``.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import g2_pilot as g2  # noqa: E402

PATH_KEYS = {
    "dec": "logp_decode",
    "pre": "logp_prefill",
    "r1": "logp_r1_fla_chunk_bf16",
    "r3": "logp_r3_fla_recurrent_bf16",
    "r4": "logp_r4_torch_fp32",
}
COMPARISONS = [
    ("dec", "r1"),
    ("dec", "r3"),
    ("dec", "r4"),
    ("r1", "r4"),
    ("pre", "r4"),
    ("dec", "pre"),
    ("pre", "r1"),
    ("r3", "r4"),
    ("r1", "r3"),
]
LABELS = {
    "dec": "vLLM decode (rollout)",
    "pre": "vLLM prefill recompute",
    "r1": "HF+FLA chunk bf16 (trainer)",
    "r3": "HF+FLA fused_recurrent bf16",
    "r4": "fp32 reference",
}


# --------------------------------------------------------------------------- pack


def pack_model(rollout_dir: Path, tf_dir: Path, model_id: str) -> dict[str, np.ndarray] | None:
    tokens_path = rollout_dir / model_id / "tokens.npz"
    tf_path = tf_dir / f"tf-{model_id}.npz"
    if not tokens_path.is_file() or not tf_path.is_file():
        return None
    roll = np.load(tokens_path)
    tf = np.load(tf_path)
    roll_ids = json.loads((rollout_dir / model_id / "sequences.json").read_text())["sequence_order"]
    tf_seqs = json.loads((tf_dir / f"tf-{model_id}-sequences.json").read_text())
    if [s["sequence_id"] for s in tf_seqs] != roll_ids:
        raise ValueError(f"{model_id}: sequence order differs between the two jobs")
    if not np.array_equal(roll["offsets"], tf["offsets"]) or not np.array_equal(
        roll["token_ids"], tf["token_ids"]
    ):
        raise ValueError(f"{model_id}: tokens differ between the two jobs")
    offsets = roll["offsets"]
    prompt_len = roll["prompt_len"]
    n_seq = len(prompt_len)
    seq = np.repeat(np.arange(n_seq, dtype=np.int32), np.diff(offsets))
    within = np.arange(offsets[-1], dtype=np.int64) - offsets[:-1][seq]
    position = (prompt_len[seq] + within).astype(np.int32)
    anchor = tf[PATH_KEYS["r1"]].astype(np.float32)
    packed: dict[str, np.ndarray] = {
        "offsets": offsets,
        "prompt_len": prompt_len,
        "seed": np.asarray([s["seed"] for s in tf_seqs], dtype=np.int16),
        "prompt_index": np.asarray([s["prompt_index"] for s in tf_seqs], dtype=np.int16),
        "position": position,
        "logp_r1": anchor,
        "ent_r1": tf["ent_r1_fla_chunk_bf16"].astype(np.float16),
    }
    if "ent_r4_torch_fp32" in tf:
        packed["ent_r4"] = tf["ent_r4_torch_fp32"].astype(np.float16)
    sources = {"dec": roll["logp_decode"], "pre": roll["logp_prefill"]}
    for key in ("r3", "r4"):
        if PATH_KEYS[key] in tf:
            sources[key] = tf[PATH_KEYS[key]]
    for key, values in sources.items():
        packed[f"d_{key}"] = (values.astype(np.float64) - anchor.astype(np.float64)).astype(
            np.float16
        )
    return packed


def pack_main(args: argparse.Namespace) -> int:
    config = g2.load_config()
    out: dict[str, np.ndarray] = {}
    meta: dict[str, Any] = {"experiment_id": config["experiment_id"], "models": {}}
    for model_id in config["models"]:
        packed = pack_model(Path(args.rollouts), Path(args.teacher_force), model_id)
        if packed is None:
            meta["models"][model_id] = "missing"
            continue
        meta["models"][model_id] = {
            "sequences": int(len(packed["prompt_len"])),
            "tokens": int(packed["offsets"][-1]),
        }
        for key, value in packed.items():
            out[f"{model_id}::{key}"] = value
    out["meta_json"] = np.frombuffer(json.dumps(meta, sort_keys=True).encode(), dtype=np.uint8)
    np.savez_compressed(args.output, **out)
    print(json.dumps(meta, indent=2, sort_keys=True))
    return 0


def load_per_token(path: Path) -> dict[str, dict[str, np.ndarray]]:
    raw = np.load(path)
    models: dict[str, dict[str, np.ndarray]] = {}
    for name in raw.files:
        if "::" not in name:
            continue
        model_id, key = name.split("::", 1)
        models.setdefault(model_id, {})[key] = raw[name]
    return models


def path_logp(data: dict[str, np.ndarray], key: str) -> np.ndarray | None:
    anchor = data["logp_r1"].astype(np.float64)
    if key == "r1":
        return anchor
    diff = data.get(f"d_{key}")
    if diff is None:
        return None
    return anchor + diff.astype(np.float64)


# --------------------------------------------------------------------------- statistics


def seq_stats(seq: np.ndarray, x: np.ndarray, y: np.ndarray, n_seq: int) -> np.ndarray:
    """Per-sequence sufficient statistics [n, sx, sy, sxy, sxx] for an OLS slope."""

    stats = np.zeros((n_seq, 5))
    stats[:, 0] = np.bincount(seq, minlength=n_seq)
    stats[:, 1] = np.bincount(seq, weights=x, minlength=n_seq)
    stats[:, 2] = np.bincount(seq, weights=y, minlength=n_seq)
    stats[:, 3] = np.bincount(seq, weights=x * y, minlength=n_seq)
    stats[:, 4] = np.bincount(seq, weights=x * x, minlength=n_seq)
    return stats


def ols_slope(total: np.ndarray) -> float:
    n, sx, sy, sxy, sxx = total
    denominator = sxx - sx * sx / n
    return float((sxy - sx * sy / n) / denominator) if n > 1 and denominator > 0 else float("nan")


def bootstrap_slope(stats: np.ndarray, reps: int, seed: int) -> tuple[float, float, float]:
    """Slope and a 95% percentile CI, resampling sequences with replacement."""

    used = stats[stats[:, 0] > 0]
    point = ols_slope(used.sum(0))
    if len(used) < 3:
        return point, float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(used), size=(reps, len(used)))
    totals = used[draws].sum(1)
    n, sx, sy, sxy, sxx = totals.T
    with np.errstate(divide="ignore", invalid="ignore"):
        slopes = (sxy - sx * sy / n) / (sxx - sx * sx / n)
    slopes = slopes[np.isfinite(slopes)]
    return point, float(np.percentile(slopes, 2.5)), float(np.percentile(slopes, 97.5))


def within_bin_slope(
    seq: np.ndarray, groups: np.ndarray, x: np.ndarray, y: np.ndarray, n_seq: int,
    reps: int, seed: int,
) -> tuple[float, float, float]:  # fmt: skip
    """OLS slope of y on x with group fixed effects; 95% CI by resampling sequences."""

    n_groups = int(groups.max()) + 1 if len(groups) else 0
    stats = np.zeros((n_seq, n_groups, 5))
    for group in range(n_groups):
        mask = groups == group
        if mask.any():
            stats[:, group, :] = seq_stats(seq[mask], x[mask], y[mask], n_seq)

    def slope(total: np.ndarray) -> np.ndarray:
        n, sx, sy, sxy, sxx = np.moveaxis(total, -1, 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            cxy = np.where(n > 0, sxy - sx * sy / np.where(n > 0, n, 1), 0.0)
            cxx = np.where(n > 0, sxx - sx * sx / np.where(n > 0, n, 1), 0.0)
            return cxy.sum(-1) / cxx.sum(-1)

    used = stats[stats[:, :, 0].sum(1) > 0]
    point = float(slope(used.sum(0)))
    if len(used) < 3:
        return point, float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(used), size=(reps, len(used)))
    slopes = slope(used[draws].sum(1))
    slopes = slopes[np.isfinite(slopes)]
    return point, float(np.percentile(slopes, 2.5)), float(np.percentile(slopes, 97.5))


def within_sequence_slope(
    seq: np.ndarray, cells: np.ndarray | None, x: np.ndarray, y: np.ndarray, n_seq: int,
    reps: int, seed: int,
) -> tuple[float, float, float]:  # fmt: skip
    """OLS slope of y on x with sequence fixed effects; 95% CI by resampling sequences.

    With ``cells`` (for example entropy bins) the fixed effects are sequence-by-cell, so the
    slope compares positions only within one sequence and one cell. Each sequence's centred
    cross-products are summed, so a resampled sequence keeps its own means.
    """

    n_cells = int(cells.max()) + 1 if cells is not None and len(cells) else 1
    key = seq.astype(np.int64) * n_cells + (cells if cells is not None else 0)
    size = n_seq * n_cells
    n = np.bincount(key, minlength=size).astype(float)
    sx = np.bincount(key, weights=x, minlength=size)
    sy = np.bincount(key, weights=y, minlength=size)
    sxy = np.bincount(key, weights=x * y, minlength=size)
    sxx = np.bincount(key, weights=x * x, minlength=size)
    safe = np.where(n > 0, n, 1.0)
    cxy = np.where(n > 0, sxy - sx * sy / safe, 0.0).reshape(n_seq, n_cells).sum(1)
    cxx = np.where(n > 0, sxx - sx * sx / safe, 0.0).reshape(n_seq, n_cells).sum(1)
    present = n.reshape(n_seq, n_cells).sum(1) > 0
    cxy, cxx = cxy[present], cxx[present]
    point = float(cxy.sum() / cxx.sum()) if cxx.sum() > 0 else float("nan")
    if len(cxy) < 3:
        return point, float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(cxy), size=(reps, len(cxy)))
    with np.errstate(divide="ignore", invalid="ignore"):
        slopes = cxy[draws].sum(1) / cxx[draws].sum(1)
    slopes = slopes[np.isfinite(slopes)]
    return point, float(np.percentile(slopes, 2.5)), float(np.percentile(slopes, 97.5))


def entropy_groups(entropy: np.ndarray, edges: Any) -> np.ndarray:
    """Index of each entropy's bin [edges[i], edges[i+1]); the last bin is open above."""

    bounds = np.asarray(g2.numeric_edges(list(edges), "entropy_edges"), dtype=np.float64)
    return np.clip(np.searchsorted(bounds, entropy, side="right") - 1, 0, len(bounds) - 2)


def bin_table(
    position: np.ndarray, seq: np.ndarray, a: np.ndarray, b: np.ndarray, width: int,
    band: tuple[float, float], with_decode: bool, entropy: np.ndarray, groups: np.ndarray,
) -> list[dict[str, Any]]:  # fmt: skip
    """Per-position-bin mismatch rows for d = a - b.

    ``mean_abs_entropy_standardized`` reweights the bin's per-entropy-bin means to the
    entropy-bin shares of all the comparison's tokens (shares renormalised over the entropy
    bins present in the position bin), so it removes the change in entropy mix with position.
    """

    d = a - b
    absd = np.abs(d)
    bins = position // width
    n_groups = int(groups.max()) + 1 if len(groups) else 0
    shares = np.bincount(groups, minlength=n_groups) / max(len(groups), 1)
    rows = []
    for index in np.unique(bins):
        mask = bins == index
        g_n = np.bincount(groups[mask], minlength=n_groups)
        g_s = np.bincount(groups[mask], weights=absd[mask], minlength=n_groups)
        present = g_n > 0
        standardized = float(
            np.sum(shares[present] * g_s[present] / g_n[present]) / shares[present].sum()
        )
        row: dict[str, Any] = {
            "bin": int(index),
            "start": int(index * width),
            "tokens": int(mask.sum()),
            "sequences": int(len(np.unique(seq[mask]))),
            "mean_abs": float(absd[mask].mean()),
            "p99_abs": float(np.percentile(absd[mask], 99)),
            "mean_signed": float(d[mask].mean()),
            "mean_entropy_r1": float(entropy[mask].mean()),
            "mean_abs_entropy_standardized": standardized,
        }
        if with_decode:
            log_ratio = b[mask] - a[mask]  # log p_B - log p_dec
            row["k3"] = float(np.mean(np.expm1(log_ratio) - log_ratio))
            ratio = np.exp(log_ratio)
            row["share_ratio_outside_band"] = float(np.mean((ratio < band[0]) | (ratio > band[1])))
        rows.append(row)
    return rows


def curve_ci(
    position: np.ndarray, seq: np.ndarray, absd: np.ndarray, n_seq: int, width: int,
    reps: int, seed: int,
) -> dict[int, tuple[float, float]]:  # fmt: skip
    """95% bootstrap CI of each bin's mean |d|, resampling sequences."""

    bins = position // width
    rng = np.random.default_rng(seed)
    out: dict[int, tuple[float, float]] = {}
    for index in np.unique(bins):
        mask = bins == index
        n = np.bincount(seq[mask], minlength=n_seq).astype(float)
        s = np.bincount(seq[mask], weights=absd[mask], minlength=n_seq)
        keep = n > 0
        n, s = n[keep], s[keep]
        if len(n) < 3:
            out[int(index)] = (float("nan"), float("nan"))
            continue
        draws = rng.integers(0, len(n), size=(reps, len(n)))
        means = s[draws].sum(1) / n[draws].sum(1)
        out[int(index)] = (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))
    return out


# --------------------------------------------------------------------------- analyze


def comparison_block(
    data: dict[str, np.ndarray], a_key: str, b_key: str, mask: np.ndarray, settings: dict[str, Any]
) -> dict[str, Any] | None:
    a = path_logp(data, a_key)
    b = path_logp(data, b_key)
    if a is None or b is None:
        return None
    offsets = data["offsets"]
    n_seq = len(offsets) - 1
    seq_all = np.repeat(np.arange(n_seq), np.diff(offsets))
    valid = mask & np.isfinite(a) & np.isfinite(b)
    if not valid.any():
        return None
    position = data["position"][valid].astype(np.int64)
    seq = seq_all[valid]
    av, bv = a[valid], b[valid]
    absd = np.abs(av - bv)
    width = settings["position_bin"]
    reps = settings["bootstrap_reps"]
    seed = settings["bootstrap_seed"]
    with_decode = a_key == "dec"
    entropy = data["ent_r1"].astype(np.float64)[valid]
    edges = g2.numeric_edges(settings["entropy_edges"], "entropy_edges")
    groups = entropy_groups(entropy, edges)
    rows = bin_table(
        position, seq, av, bv, width, tuple(settings["ratio_band"]), with_decode, entropy, groups
    )
    ci = curve_ci(position, seq, absd, n_seq, width, reps, seed)
    for row in rows:
        row["mean_abs_ci95"] = list(ci[row["bin"]])
    x = position / 1000.0
    slope, lo, hi = bootstrap_slope(seq_stats(seq, x, absd, n_seq), reps, seed)
    fe_slope, fe_lo, fe_hi = within_bin_slope(seq, groups, x, absd, n_seq, reps, seed)
    sq_slope, sq_lo, sq_hi = within_sequence_slope(seq, None, x, absd, n_seq, reps, seed)
    se_slope, se_lo, se_hi = within_sequence_slope(seq, groups, x, absd, n_seq, reps, seed)
    by_entropy = []
    for group in range(len(edges) - 1):
        gmask = groups == group
        if gmask.sum() < 100:
            continue
        s, slo, shi = bootstrap_slope(
            seq_stats(seq[gmask], x[gmask], absd[gmask], n_seq), reps, seed
        )
        by_entropy.append(
            {
                "entropy_lo": float(edges[group]),
                "entropy_hi": float(edges[group + 1]),
                "tokens": int(gmask.sum()),
                "mean_abs": float(absd[gmask].mean()),
                "p99_abs": float(np.percentile(absd[gmask], 99)),
                "sequences": int(len(np.unique(seq[gmask]))),
                "slope_per_1k": s,
                "slope_ci95": [slo, shi],
                "mean_position": float(position[gmask].mean()),
            }
        )
    per_seq_mean = np.bincount(seq, weights=absd, minlength=n_seq) / np.maximum(
        np.bincount(seq, minlength=n_seq), 1
    )
    present = np.bincount(seq, minlength=n_seq) > 0
    block: dict[str, Any] = {
        "a": a_key,
        "b": b_key,
        "tokens": int(valid.sum()),
        "sequences": int(present.sum()),
        "mean_abs": float(absd.mean()),
        "p99_abs": float(np.percentile(absd, 99)),
        "max_abs": float(absd.max()),
        "slope_per_1k": slope,
        "slope_ci95": [lo, hi],
        "slope_within_entropy_bins_per_1k": fe_slope,
        "slope_within_entropy_bins_ci95": [fe_lo, fe_hi],
        "slope_within_sequences_per_1k": sq_slope,
        "slope_within_sequences_ci95": [sq_lo, sq_hi],
        "slope_within_sequence_entropy_cells_per_1k": se_slope,
        "slope_within_sequence_entropy_cells_ci95": [se_lo, se_hi],
        "mean_entropy_r1": float(entropy.mean()),
        "by_position": rows,
        "by_entropy": by_entropy,
        "per_sequence_mean_abs": {
            "min": float(per_seq_mean[present].min()),
            "q25": float(np.percentile(per_seq_mean[present], 25)),
            "median": float(np.median(per_seq_mean[present])),
            "q75": float(np.percentile(per_seq_mean[present], 75)),
            "max": float(per_seq_mean[present].max()),
        },
    }
    if with_decode:
        log_ratio = bv - av
        block["k3"] = float(np.mean(np.expm1(log_ratio) - log_ratio))
        ratio = np.exp(log_ratio)
        band = settings["ratio_band"]
        block["share_ratio_outside_band"] = float(np.mean((ratio < band[0]) | (ratio > band[1])))
    return block


def analyze(models: dict[str, dict[str, np.ndarray]], settings: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"settings": settings, "models": {}}
    for model_id, data in models.items():
        offsets = data["offsets"]
        seeds = data["seed"]
        seq_all = np.repeat(np.arange(len(seeds)), np.diff(offsets))
        token_seed = seeds[seq_all]
        model_out: dict[str, Any] = {
            "sequences": int(len(seeds)),
            "tokens": int(offsets[-1]),
            "seeds": sorted(int(s) for s in np.unique(seeds)),
            "completion_len": {
                "median": float(np.median(np.diff(offsets))),
                "max": int(np.diff(offsets).max()),
                "min": int(np.diff(offsets).min()),
            },
            "subsets": {},
        }
        subsets = {"all_seeds": np.ones(len(token_seed), dtype=bool)}
        for seed in np.unique(seeds):
            subsets[f"seed_{int(seed)}"] = token_seed == seed
        for name, mask in subsets.items():
            blocks = {}
            for a_key, b_key in COMPARISONS:
                block = comparison_block(data, a_key, b_key, mask, settings)
                if block is not None:
                    blocks[f"{a_key}_vs_{b_key}"] = block
            model_out["subsets"][name] = blocks
        result["models"][model_id] = model_out
    return result


def fmt(value: float, digits: int = 4) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "n/a"
    if value != 0 and abs(value) < 10 ** (-digits):
        return f"{value:.2e}"
    return f"{value:.{digits}f}"


def entropy_label(lo: float, hi: float) -> str:
    return f"[{lo:g}, {'inf' if hi >= 1e6 else format(hi, 'g')})"


def sci(value: float) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    return f"{value:+.2e}"


def slope_cell(block: dict[str, Any], key: str) -> str:
    lo, hi = block[f"{key}_ci95"]
    return f"{sci(block[f'{key}_per_1k'])} [{sci(lo)}, {sci(hi)}]"


def markdown_tables(result: dict[str, Any]) -> str:
    lines = [
        "# G2 pilot tables (EXPLORATORY)",
        "",
        "Slopes are of |d| on absolute position, per 1,000 tokens, with 95% bootstrap intervals "
        "over sequences: pooled OLS; with entropy-bin fixed effects (pooled across sequences); "
        "with sequence fixed effects (within sequences); with sequence-by-entropy-bin fixed "
        "effects. Entropy is that of the r1 distribution, in nats.",
        "",
    ]
    for model_id, model in result["models"].items():
        lines.append(f"## {model_id}")
        lines.append("")
        lines.append(
            f"{model['sequences']} sequences, {model['tokens']} completion tokens, seeds "
            f"{model['seeds']}, completion length median {model['completion_len']['median']:.0f}, "
            f"max {model['completion_len']['max']}."
        )
        lines.append("")
        for subset, blocks in model["subsets"].items():
            lines.append(f"### {model_id}, {subset}: summary")
            lines.append("")
            lines.append(
                "| comparison | tokens | seqs | mean abs | p99 abs | k3 | share ratio outside "
                "band | slope per 1K, pooled | within entropy bins | within sequences | "
                "within sequence x entropy bin |"
            )
            lines.append("|---|---:|---:|---:|---:|---:|---:|---|---|---|---|")
            for name, block in blocks.items():
                lines.append(
                    f"| {name} | {block['tokens']} | {block['sequences']} | "
                    f"{fmt(block['mean_abs'])} | {fmt(block['p99_abs'])} | "
                    f"{fmt(block.get('k3', float('nan')), 6)} | "
                    f"{fmt(block.get('share_ratio_outside_band', float('nan')), 5)} | "
                    f"{slope_cell(block, 'slope')} | "
                    f"{slope_cell(block, 'slope_within_entropy_bins')} | "
                    f"{slope_cell(block, 'slope_within_sequences')} | "
                    f"{slope_cell(block, 'slope_within_sequence_entropy_cells')} |"
                )
            lines.append("")
            if subset in ("all_seeds", "seed_42"):
                for name in ("dec_vs_r1", "dec_vs_r3", "dec_vs_r4", "r1_vs_r4", "dec_vs_pre",
                             "r1_vs_r3"):  # fmt: skip
                    block = blocks.get(name)
                    if block is None:
                        continue
                    lines.append(f"#### {model_id}, {subset}, {name}: by position (1K bins)")
                    lines.append("")
                    lines.append(
                        "| bin start | tokens | seqs | mean abs [95% CI] | p99 abs | k3 | "
                        "share outside band | mean r1 entropy | entropy-standardized mean abs |"
                    )
                    lines.append("|---:|---:|---:|---|---:|---:|---:|---:|---:|")
                    for row in block["by_position"]:
                        ci = row["mean_abs_ci95"]
                        lines.append(
                            f"| {row['start']} | {row['tokens']} | {row['sequences']} | "
                            f"{fmt(row['mean_abs'])} [{fmt(ci[0])}, {fmt(ci[1])}] | "
                            f"{fmt(row['p99_abs'])} | {fmt(row.get('k3', float('nan')), 6)} | "
                            f"{fmt(row.get('share_ratio_outside_band', float('nan')), 5)} | "
                            f"{fmt(row['mean_entropy_r1'], 3)} | "
                            f"{fmt(row['mean_abs_entropy_standardized'])} |"
                        )
                    lines.append("")
                    lines.append(f"#### {model_id}, {subset}, {name}: by r1 entropy")
                    lines.append("")
                    lines.append(
                        "| entropy bin (nats) | tokens | seqs | mean abs | p99 abs | "
                        "mean position | slope per 1K [95% CI] |"
                    )
                    lines.append("|---|---:|---:|---:|---:|---:|---|")
                    for row in block["by_entropy"]:
                        lines.append(
                            f"| {entropy_label(row['entropy_lo'], row['entropy_hi'])} | "
                            f"{row['tokens']} | "
                            f"{row['sequences']} | {fmt(row['mean_abs'], 5)} | "
                            f"{fmt(row['p99_abs'])} | {row['mean_position']:.0f} | "
                            f"{sci(row['slope_per_1k'])} [{sci(row['slope_ci95'][0])}, "
                            f"{sci(row['slope_ci95'][1])}] |"
                        )
                    lines.append("")
    return "\n".join(lines) + "\n"


def contrast_table(result: dict[str, Any], hybrid: str, dense: str) -> str:
    """Hybrid and dense rollout-vs-trainer mismatch side by side, per 1K bin and per entropy
    bin, on each model's seed-42 rollouts (the dense control has only that seed).

    Descriptive only: in this pilot the dense control (Qwen3-8B) is not size-matched to the
    hybrid (Qwen3.5-4B) and generated different text, so the ratios carry no hybrid-vs-dense
    comparison (README)."""

    models = result["models"]
    if hybrid not in models or dense not in models:
        return ""
    h = {r["bin"]: r for r in models[hybrid]["subsets"]["seed_42"]["dec_vs_r1"]["by_position"]}
    d = {r["bin"]: r for r in models[dense]["subsets"]["seed_42"]["dec_vs_r1"]["by_position"]}
    lines = [
        f"## {hybrid} vs {dense}: dec_vs_r1 per 1K bin, seed-42 rollouts",
        "",
        "| bin start | hybrid seqs | hybrid mean abs | dense seqs | dense mean abs | "
        "mean ratio | hybrid p99 | dense p99 | p99 ratio |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for index in sorted(set(h) | set(d)):
        a, b = h.get(index), d.get(index)
        if a is None or b is None:
            continue
        lines.append(
            f"| {a['start']} | {a['sequences']} | {fmt(a['mean_abs'])} | {b['sequences']} | "
            f"{fmt(b['mean_abs'])} | {a['mean_abs'] / b['mean_abs']:.2f} | {fmt(a['p99_abs'])} | "
            f"{fmt(b['p99_abs'])} | {a['p99_abs'] / b['p99_abs']:.2f} |"
        )
    he = models[hybrid]["subsets"]["seed_42"]["dec_vs_r1"]["by_entropy"]
    de = models[dense]["subsets"]["seed_42"]["dec_vs_r1"]["by_entropy"]
    he = {(r["entropy_lo"], r["entropy_hi"]): r for r in he}
    de = {(r["entropy_lo"], r["entropy_hi"]): r for r in de}
    lines += [
        "",
        f"## {hybrid} vs {dense}: dec_vs_r1 per r1-entropy bin, seed-42 rollouts",
        "",
        "| entropy bin (nats) | hybrid tokens | hybrid mean abs | dense tokens | dense mean abs | "
        "mean ratio |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key in sorted(set(he) & set(de)):
        a, b = he[key], de[key]
        lines.append(
            f"| {entropy_label(*key)} | {a['tokens']} | {fmt(a['mean_abs'], 5)} | {b['tokens']} | "
            f"{fmt(b['mean_abs'], 5)} | {a['mean_abs'] / b['mean_abs']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def plot(result: dict[str, Any], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {
        "dec_vs_r1": "#1f77b4",
        "dec_vs_r3": "#17becf",
        "dec_vs_r4": "#d62728",
        "r1_vs_r4": "#2ca02c",
        "dec_vs_pre": "#9467bd",
        "pre_vs_r4": "#8c564b",
        "r3_vs_r4": "#ff7f0e",
        "r1_vs_r3": "#7f7f7f",
    }
    models = list(result["models"])
    fig, axes = plt.subplots(2, 2, figsize=(13, 9.5), gridspec_kw={"hspace": 0.32, "wspace": 0.22})
    axes = axes.ravel()
    position_axes = [axes[0], axes[1], axes[2]]

    def draw(ax: Any, block: dict[str, Any], label: str, color: str, style: str = "-") -> None:
        rows = [r for r in block["by_position"] if r["tokens"] >= 200]
        x = [r["start"] / 1000 + 0.5 for r in rows]
        y = [r["mean_abs"] for r in rows]
        lo = [r["mean_abs_ci95"][0] for r in rows]
        hi = [r["mean_abs_ci95"][1] for r in rows]
        ax.plot(x, y, style, color=color, label=label, marker="o", markersize=3)
        ax.fill_between(x, lo, hi, color=color, alpha=0.15, linewidth=0)

    for ax, model_id in zip(position_axes[:2], models, strict=False):
        blocks = result["models"][model_id]["subsets"].get("seed_42", {})
        for name, color in colors.items():
            if name in blocks:
                a, b = name.split("_vs_")
                draw(ax, blocks[name], f"{LABELS[a]} vs {LABELS[b]}", color)
        ax.set_yscale("log")
        ax.set_title(f"{model_id}: paths, seed 42 rollouts")
        ax.set_xlabel("absolute token position (K), 1K bins")
        ax.set_ylabel("mean |Δ log p| per token")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=7)
    ax = position_axes[2]
    for model_id, style in zip(models, ["-", "--"], strict=False):
        model = result["models"][model_id]
        for subset, blocks in model["subsets"].items():
            if not subset.startswith("seed_") or "dec_vs_r1" not in blocks:
                continue
            seed = subset.split("_")[1]
            color = {"42": "#1f77b4", "43": "#17becf", "44": "#bcbd22"}.get(seed, "#333333")
            if model_id != models[0]:
                color = "#d62728"
            draw(ax, blocks["dec_vs_r1"], f"{model_id} seed {seed}", color, style)
    hybrid_all = result["models"][models[0]]["subsets"]["all_seeds"].get("dec_vs_r1")
    if hybrid_all is not None:
        rows = [r for r in hybrid_all["by_position"] if r["tokens"] >= 200]
        x = [r["start"] / 1000 + 0.5 for r in rows]
        ax.plot(x, [r["mean_abs"] for r in rows], "-", color="#000000", linewidth=1.6,
                label=f"{models[0]} all seeds")  # fmt: skip
        ax.plot(x, [r["mean_abs_entropy_standardized"] for r in rows], ":", color="#000000",
                linewidth=1.6, label=f"{models[0]} all seeds, entropy-standardized")  # fmt: skip
    ax.set_yscale("log")
    ax.set_title("rollout vs trainer (dec vs r1), per seed")
    ax.set_xlabel("absolute token position (K), 1K bins")
    ax.set_ylabel("mean |Δ log p| per token")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=7)
    shared = [a.get_ylim() for a in position_axes]
    for a in position_axes:
        a.set_ylim(min(lo for lo, _ in shared), max(hi for _, hi in shared))
    # Entropy panel: rollout vs trainer by r1-entropy bin, each model's seed-42 rollouts.
    ax = axes[3]
    for model_id, color in zip(models, ["#1f77b4", "#d62728"], strict=False):
        block = result["models"][model_id]["subsets"].get("seed_42", {}).get("dec_vs_r1")
        if block is None:
            continue
        rows = block["by_entropy"]
        labels = [entropy_label(r["entropy_lo"], r["entropy_hi"]) for r in rows]
        ax.plot(range(len(rows)), [r["mean_abs"] for r in rows], "-o", color=color,
                label=f"{model_id}", markersize=4)  # fmt: skip
        ax.set_xticks(range(len(rows)), labels, fontsize=7)
    ax.set_yscale("log")
    ax.set_title("rollout vs trainer (dec vs r1) by token entropy, seed 42")
    ax.set_xlabel("entropy of the r1 distribution (nats), bins")
    ax.set_ylabel("mean |Δ log p| per token")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=7)
    fig.suptitle("G2 pilot (EXPLORATORY): per-token log-prob mismatch by position; bands: 95% "
                 "bootstrap over sequences", fontsize=10)  # fmt: skip
    fig.savefig(output, dpi=130, bbox_inches="tight")
    plt.close(fig)


def analyze_main(args: argparse.Namespace) -> int:
    config = g2.load_config()
    settings = dict(config["analysis"])
    models = load_per_token(Path(args.per_token))
    result = analyze(models, settings)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    g2.write_json(out / "analysis.json", result)
    (out / "tables.md").write_text(
        markdown_tables(result) + "\n" + contrast_table(result, "qwen3.5-4b", "qwen3-8b"),
        encoding="utf-8",
    )
    plot(result, out / "mismatch-by-position.png")
    print(json.dumps({"written": ["analysis.json", "tables.md", "mismatch-by-position.png"]}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack", allow_abbrev=False)
    pack.add_argument("--rollouts", required=True)
    pack.add_argument("--teacher-force", required=True)
    pack.add_argument("--output", required=True)
    an = sub.add_parser("analyze", allow_abbrev=False)
    an.add_argument("--per-token", required=True)
    an.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    return pack_main(args) if args.command == "pack" else analyze_main(args)


if __name__ == "__main__":
    sys.exit(main())
