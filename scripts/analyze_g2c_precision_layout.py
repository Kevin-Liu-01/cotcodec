#!/usr/bin/env python3
"""g2c-precision-layout-v1 (EXPLORATORY): place fp32 and bf16 (G2b), fp16 and bf16_b528 side by
side.

CPU only. Subcommands:

* ``pack --model M --rollouts DIR --teacher-force DIR --output F``: one per-token file per model
  for this experiment's two arms. DIR is the rollout job's output directory (``<model>-<arm>/``
  worker dirs with ``tokens.npz`` and ``sequences.json``; ``prefill-<arm>.npz`` and ``.json``);
  the teacher-forcing dir holds ``tf-<model>.npz``. Token ids are checked equal across the
  rollouts, the prefill and teacher forcing. Per completion token: ``d_dec``, ``d_pre`` (vLLM
  prefill in the arm's own state dtype and block size) and ``d_r4`` as fp16 differences from
  the trainer path r1 (G2b's encoding), and the r1 and r4 entropies.
* ``rollouts --rollout-jobs DIR... --output F``: per arm, the engine record (block size, block
  pool, GDN page padding), log facts, phase summaries, the prefill engines, the smoke probe and
  per-rollout records (length, how it ended, boxed answer, tail compressibility).
* ``analyze --per-token F... --g2b-per-token F... --rollouts F --g2b-throughput F
  --output-dir D``: tables (JSON, Markdown) and the figure. G2b's arms come from G2b's
  committed per-token files (checked against the SHA-256 in the config) and throughput.json;
  their numbers are recomputed with the same code and checked against G2b's analysis.json.

The metric is G2b's: d = log p_A - log p_B on the rollout's own tokens; mean and p99 |d|; k3 and
the share of importance ratios outside [0.8, 1.25] against the decode path; slopes of |d| on
position per 1,000 tokens, pooled, within entropy bins, within sequences and within sequence x
entropy-bin cells (scripts/analyze_g2_pilot.py). Arm contrasts bootstrap over the 24 prompts
jointly (all four arms share them), 2,000 draws, seed 42. The excess fraction of an arm is
(arm - fp32) / (bf16 - fp32): 0 means fp32-like, 1 means as far off as G2b's bf16 arm.
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
from harness import g2b_state_dtype as gb  # noqa: E402
from harness import g2c_precision_layout as gc  # noqa: E402
from scripts import analyze_g2_pilot as ap  # noqa: E402
from scripts import analyze_g2b_state_dtype as ab  # noqa: E402

ARMS = gc.ALL_ARMS
NEW_ARMS = gc.ARM_NAMES
COMPARISONS = [
    ("dec", "r1"),
    ("dec", "r4"),
    ("dec", "pre"),
    ("pre", "r1"),
    ("r1", "r4"),
    ("pre", "r4"),
]
#: Arms compared, each against the two references.
CONTRAST_ARMS = ("bf16", "fp16", "bf16_b528")
LENGTHS = [4096, 8192, 16384, 24576, 28672, 32768]
#: The figure's encoding: hue is the state dtype, line style the block layout.
STYLE = {
    "fp32": {"color": "#2a78d6", "ls": "-", "label": "fp32 state, 528-token blocks (G2b)"},
    "bf16": {"color": "#eb6834", "ls": "--", "label": "bf16 state, 272-token blocks (G2b)"},
    "fp16": {"color": "#1baf7a", "ls": "--", "label": "fp16 state, 272-token blocks"},
    "bf16_b528": {"color": "#eb6834", "ls": "-", "label": "bf16 state, 528-token blocks (forced)"},
}


# --------------------------------------------------------------------------- pack


def _prefill_arm(rollout_dir: Path, arm: str) -> dict[str, Any]:
    record = json.loads((rollout_dir / f"prefill-{arm}.json").read_text(encoding="utf-8"))
    data = np.load(rollout_dir / f"prefill-{arm}.npz")
    order = record["sequence_order"]
    return {
        "index": {k: i for i, k in enumerate(order)},
        "offsets": data["offsets"],
        "logp": data["logp_prefill"].astype(np.float64),
    }


def pack_model(model_id: str, rollout_dir: Path, tf_dir: Path) -> dict[str, np.ndarray]:
    tf = np.load(tf_dir / f"tf-{model_id}.npz")
    tf_seqs = json.loads((tf_dir / f"tf-{model_id}-sequences.json").read_text(encoding="utf-8"))
    order = [s["sequence_id"] for s in tf_seqs]
    offsets = tf["offsets"]
    n_seq = len(order)
    arms = {arm: ab._load_rollout_arm(rollout_dir / f"{model_id}-{arm}") for arm in NEW_ARMS}
    for arm, loaded in arms.items():
        if loaded["arm"] != arm:
            raise ValueError(f"{model_id}: worker dir of {arm} records arm {loaded['arm']}")
    prefill = {arm: _prefill_arm(rollout_dir, arm) for arm in NEW_ARMS}
    total = int(offsets[-1])
    dec = np.full(total, np.nan)
    pre = np.full(total, np.nan)
    seq_arm = np.zeros(n_seq, dtype=np.int8)
    seq_seed = np.zeros(n_seq, dtype=np.int16)
    seq_prompt = np.zeros(n_seq, dtype=np.int16)
    finished = np.zeros(n_seq, dtype=np.int8)
    nonfinite = np.zeros(n_seq, dtype=np.int32)
    for i, seq_id in enumerate(order):
        parts = gb.parse_sequence_id(seq_id)
        if parts["model_id"] != model_id or parts["arm"] not in NEW_ARMS:
            raise ValueError(f"{seq_id}: not a {model_id} sequence of {NEW_ARMS}")
        arm = arms[parts["arm"]]
        j = arm["index"][seq_id]
        lo, hi = arm["tokens"]["offsets"][j], arm["tokens"]["offsets"][j + 1]
        if not np.array_equal(
            arm["tokens"]["token_ids"][lo:hi], tf["token_ids"][offsets[i] : offsets[i + 1]]
        ):
            raise ValueError(f"{seq_id}: tokens differ between rollout and teacher forcing")
        dec[offsets[i] : offsets[i + 1]] = arm["tokens"]["logp_decode"][lo:hi]
        p = prefill[parts["arm"]]
        k = p["index"][seq_id]
        plo, phi = int(p["offsets"][k]), int(p["offsets"][k + 1])
        if phi - plo != hi - lo:
            raise ValueError(f"{seq_id}: prefill length differs from the rollout")
        pre[offsets[i] : offsets[i + 1]] = p["logp"][plo:phi]
        seq_arm[i] = NEW_ARMS.index(parts["arm"])
        seq_seed[i] = parts["seed"]
        seq_prompt[i] = parts["prompt_index"]
        meta = arm["meta"][seq_id]
        finished[i] = 1 if meta["finish_reason"] == "stop" else 0
        nonfinite[i] = int(meta.get("nonfinite_logprobs", 0))
    r1 = tf["logp_r1"].astype(np.float64)
    out: dict[str, np.ndarray] = {
        "offsets": offsets,
        "prompt_len": tf["prompt_len"],
        "arm": seq_arm,
        "seed": seq_seed,
        "prompt_index": seq_prompt,
        "finished": finished,
        "nonfinite_decode": nonfinite,
        "ent_r1": tf["ent_r1"].astype(np.float16),
        "ent_r4": tf["ent_r4"].astype(np.float16)
        if "ent_r4" in tf
        else np.full(total, np.nan, np.float16),
        "d_dec": (dec - r1).astype(np.float16),
        "d_pre": (pre - r1).astype(np.float16),
    }
    if "logp_r4" in tf:
        out["d_r4"] = (tf["logp_r4"].astype(np.float64) - r1).astype(np.float16)
    return out


def pack_main(args: argparse.Namespace) -> int:
    packed = pack_model(args.model, Path(args.rollouts), Path(args.teacher_force))
    meta = {
        "experiment_id": gc.EXPERIMENT_ID,
        "model": args.model,
        "arms": list(NEW_ARMS),
        "sequences": int(len(packed["prompt_len"])),
        "tokens": int(packed["offsets"][-1]),
    }
    packed["meta_json"] = np.frombuffer(json.dumps(meta, sort_keys=True).encode(), dtype=np.uint8)
    np.savez_compressed(args.output, **packed)
    print(json.dumps(meta, sort_keys=True))
    return 0


# --------------------------------------------------------------------------- joined data


def combine(g2b_raw: dict[str, np.ndarray], g2c_raw: dict[str, np.ndarray]) -> dict[str, Any]:
    """One model's four arms as one per-token set (G2b's sequences first). Arm codes index
    ARMS; d_pre is the prefill in the arm's own state dtype (G2b: pre32 or pre16)."""

    parts = []
    for raw, codes in ((g2b_raw, (0, 1)), (g2c_raw, (2, 3))):
        arm = np.asarray([codes[int(a)] for a in raw["arm"]], dtype=np.int8)
        lengths = np.diff(raw["offsets"])
        token_arm = np.repeat(raw["arm"], lengths)
        if "d_pre" in raw:
            d_pre = raw["d_pre"]
        else:
            d_pre = np.where(token_arm == 0, raw["d_pre32"], raw["d_pre16"])
        total = int(raw["offsets"][-1])
        nan = np.full(total, np.nan, np.float16)
        parts.append(
            {
                "lengths": lengths,
                "prompt_len": raw["prompt_len"],
                "arm": arm,
                "seed": raw["seed"],
                "prompt_index": raw["prompt_index"],
                "finished": raw["finished"],
                "ent_r1": raw["ent_r1"],
                "d_dec": raw["d_dec"],
                "d_pre": d_pre,
                "d_r4": raw.get("d_r4", nan),
            }
        )
    lengths = np.concatenate([p["lengths"] for p in parts])
    offsets = np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)
    out: dict[str, Any] = {"offsets": offsets}
    for key in ("prompt_len", "arm", "seed", "prompt_index", "finished"):
        out[key] = np.concatenate([p[key] for p in parts])
    for key in ("ent_r1", "d_dec", "d_pre", "d_r4"):
        out[key] = np.concatenate([np.asarray(p[key]) for p in parts]).astype(np.float64)
    out["position"] = ab.token_positions(offsets, out["prompt_len"])
    out["seq"] = np.repeat(np.arange(len(lengths)), lengths)
    out["arm_token"] = out["arm"][out["seq"]]
    out["seed_token"] = out["seed"][out["seq"]]
    out["logp_r1"] = np.zeros(int(offsets[-1]))
    return out


# --------------------------------------------------------------------------- statistics


def sequence_stats(data: dict[str, Any], a_key: str, b_key: str, edges: list[float]) -> np.ndarray:
    """G2b's per-sequence sums [n, sum |d|, slope sums x2, x2, sum k3] plus the count of ratios
    outside the band (decode path only)."""

    stats = ab.sequence_stats(data, a_key, b_key, np.ones(len(data["seq"]), dtype=bool), edges)
    extra = np.zeros((stats.shape[0], 1))
    if a_key == "dec":
        a = ap.path_logp(data, a_key)
        b = ap.path_logp(data, b_key)
        valid = np.isfinite(a) & np.isfinite(b)
        ratio = np.exp(b[valid] - a[valid])
        outside = ((ratio < 0.8) | (ratio > 1.25)).astype(float)
        extra[:, 0] = np.bincount(data["seq"][valid], weights=outside, minlength=stats.shape[0])
    return np.concatenate([stats, extra], axis=1)


def _measures(sums: np.ndarray) -> dict[str, np.ndarray]:
    n = sums[..., 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        return {
            "mean_abs": sums[..., 1] / n,
            "k3": sums[..., 6] / n,
            "share_outside_band": sums[..., 7] / n,
            "slope_within_sequences_per_1k": sums[..., 2] / sums[..., 3],
            "slope_within_sequence_entropy_cells_per_1k": sums[..., 4] / sums[..., 5],
        }


def _ci(values: np.ndarray) -> list[float] | None:
    values = values[np.isfinite(values)]
    if not len(values):
        return None
    return [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]


def arm_contrasts(stats: np.ndarray, data: dict[str, Any], reps: int, seed: int) -> dict[str, Any]:
    """Per arm point values with 95% CIs, and each arm against fp32 and bf16 (ratio, difference,
    excess fraction), bootstrapping the prompts jointly across the four arms."""

    seq_arm, seq_prompt = data["arm"], data["prompt_index"]
    present = stats[:, 0] > 0
    arms_present = [a for i, a in enumerate(ARMS) if (present & (seq_arm == i)).any()]
    prompt_sets = [set(seq_prompt[present & (seq_arm == ARMS.index(a))]) for a in arms_present]
    prompts = sorted(set.intersection(*prompt_sets)) if prompt_sets else []
    if len(prompts) < 3:
        return {"prompts": len(prompts)}
    index = {p: k for k, p in enumerate(prompts)}
    per = np.zeros((len(ARMS), len(prompts), stats.shape[1]))
    for i in np.nonzero(present)[0]:
        k = index.get(int(seq_prompt[i]))
        if k is not None:
            per[int(seq_arm[i]), k] += stats[i]
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(prompts), size=(reps, len(prompts)))
    counts = np.stack([np.bincount(row, minlength=len(prompts)) for row in draws]).astype(float)
    point = {a: _measures(per[ARMS.index(a)].sum(0)) for a in arms_present}
    boot = {a: _measures(counts @ per[ARMS.index(a)]) for a in arms_present}
    out: dict[str, Any] = {"prompts": len(prompts), "arms": {}, "pairs": {}}
    for arm in arms_present:
        out["arms"][arm] = {
            name: {"value": float(point[arm][name]), "ci95": _ci(boot[arm][name])}
            for name in point[arm]
        }
        out["arms"][arm]["sequences"] = int((present & (seq_arm == ARMS.index(arm))).sum())
    for arm in CONTRAST_ARMS:
        if arm not in point:
            continue
        for ref in ("fp32", "bf16"):
            if ref == arm or ref not in point:
                continue
            pair: dict[str, Any] = {}
            for name in point[arm]:
                a, r = float(point[arm][name]), float(point[ref][name])
                record: dict[str, Any] = {"arm": a, "ref": r, "diff": a - r}
                record["diff_ci95"] = _ci(boot[arm][name] - boot[ref][name])
                if name in ("mean_abs", "k3", "share_outside_band") and r > 0:
                    with np.errstate(divide="ignore", invalid="ignore"):
                        record["ratio"] = a / r
                        record["ratio_ci95"] = _ci(boot[arm][name] / boot[ref][name])
                pair[name] = record
            out["pairs"][f"{arm}_vs_{ref}"] = pair
        if arm != "bf16" and {"fp32", "bf16"} <= set(point):
            excess = {}
            for name in ("mean_abs", "k3", "slope_within_sequences_per_1k"):
                f, b, a = (float(point[x][name]) for x in ("fp32", "bf16", arm))
                with np.errstate(divide="ignore", invalid="ignore"):
                    draws_x = (boot[arm][name] - boot["fp32"][name]) / (
                        boot["bf16"][name] - boot["fp32"][name]
                    )
                excess[name] = {
                    "value": (a - f) / (b - f) if b != f else float("nan"),
                    "ci95": _ci(draws_x),
                }
            out["pairs"][f"{arm}_excess_fraction"] = excess
    return out


def position_ratios(
    data: dict[str, Any], a_key: str, b_key: str, width: int, reps: int, seed: int
) -> list[dict[str, Any]]:
    """Per position bin: each arm's mean |d|, tokens and sequences, and each arm's ratio to fp32
    with a 95% bootstrap over prompts (drawn jointly)."""

    a = ap.path_logp(data, a_key)
    b = ap.path_logp(data, b_key)
    valid = np.isfinite(a) & np.isfinite(b)
    bins = data["position"] // width
    prompts = sorted(set(data["prompt_index"].tolist()))
    pindex = {p: k for k, p in enumerate(prompts)}
    tok_prompt = np.asarray([pindex[int(p)] for p in data["prompt_index"]])[data["seq"]]
    absd = np.abs(a - b)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(prompts), size=(reps, len(prompts)))
    counts = np.stack([np.bincount(row, minlength=len(prompts)) for row in draws]).astype(float)
    rows = []
    for index_bin in np.unique(bins[valid]):
        row: dict[str, Any] = {"start": int(index_bin * width)}
        sums = {}
        for code, arm in enumerate(ARMS):
            m = valid & (bins == index_bin) & (data["arm_token"] == code)
            row[f"{arm}_tokens"] = int(m.sum())
            row[f"{arm}_sequences"] = int(len(np.unique(data["seq"][m])))
            row[f"{arm}_mean_abs"] = float(absd[m].mean()) if m.any() else float("nan")
            sums[arm] = (
                np.bincount(tok_prompt[m], minlength=len(prompts)).astype(float),
                np.bincount(tok_prompt[m], weights=absd[m], minlength=len(prompts)),
            )
        if row["fp32_tokens"]:
            with np.errstate(divide="ignore", invalid="ignore"):
                ref = counts @ sums["fp32"][1] / (counts @ sums["fp32"][0])
                for arm in ARMS[1:]:
                    if not row[f"{arm}_tokens"]:
                        continue
                    row[f"{arm}_over_fp32"] = row[f"{arm}_mean_abs"] / row["fp32_mean_abs"]
                    ratio = (counts @ sums[arm][1] / (counts @ sums[arm][0])) / ref
                    ratio = ratio[np.isfinite(ratio)]
                    if len(ratio) > reps // 2:
                        row[f"{arm}_over_fp32_ci95"] = _ci(ratio)
        rows.append(row)
    return rows


def analyze_model(data: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    edges = g2.numeric_edges(settings["entropy_edges"], "entropy_edges")
    reps, seed = int(settings["bootstrap_reps"]), int(settings["bootstrap_seed"])
    offsets = data["offsets"]
    lengths = np.diff(offsets)
    result: dict[str, Any] = {"arms": {}, "subsets": {}, "contrasts": {}}
    for code, arm in enumerate(ARMS):
        m = data["arm"] == code
        if not m.any():
            continue
        result["arms"][arm] = {
            "sequences": int(m.sum()),
            "tokens": int(lengths[m].sum()),
            "finished": int(data["finished"][m].sum()),
            "completion_len": {
                "mean": float(lengths[m].mean()),
                "median": float(np.median(lengths[m])),
                "max": int(lengths[m].max()),
                "min": int(lengths[m].min()),
            },
        }
        mask = data["arm_token"] == code
        blocks = {}
        for a_key, b_key in COMPARISONS:
            block = ap.comparison_block(data, a_key, b_key, mask, settings)
            if block is not None:
                blocks[f"{a_key}_vs_{b_key}"] = block
        result["subsets"][f"{arm}/all"] = blocks
        for s in sorted(set(data["seed"][m].tolist())):
            smask = mask & (data["seed_token"] == s)
            block = ap.comparison_block(data, "dec", "r1", smask, settings)
            if block is not None:
                result["subsets"][f"{arm}/seed_{s}"] = {"dec_vs_r1": block}
    for a_key, b_key in (("dec", "r1"), ("dec", "r4"), ("dec", "pre"), ("pre", "r1")):
        stats = sequence_stats(data, a_key, b_key, edges)
        result["contrasts"][f"{a_key}_vs_{b_key}"] = arm_contrasts(stats, data, reps, seed)
    result["position_ratios"] = {
        "dec_vs_r1": position_ratios(data, "dec", "r1", int(settings["position_bin"]), reps, seed)
    }
    return result


# --------------------------------------------------------------------------- rollouts


def rollout_job(job_dir: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Per arm of one rollout job: engine records, log facts, phases, rollouts."""

    summary = json.loads((job_dir / "summary.json").read_text(encoding="utf-8"))
    model_id = summary["model"]
    answers = {int(r["prompt_index"]): r["answer"] for r in g2.load_prompts(config)}
    gdn_layers = config["models"][model_id]["gdn_layers"]
    out = []
    for arm in NEW_ARMS:
        worker = job_dir / f"{model_id}-{arm}"
        if not (worker / "engine.json").is_file():
            continue
        engine = json.loads((worker / "engine.json").read_text(encoding="utf-8"))
        wsum_path = worker / "summary.json"
        wsum = json.loads(wsum_path.read_text(encoding="utf-8")) if wsum_path.is_file() else {}
        record: dict[str, Any] = {
            "job_dir": job_dir.name,
            "model": model_id,
            "arm": arm,
            "smoke": summary.get("smoke"),
            "state_dtype": gc.arm_state_dtype(config, arm),
            "block_size_setting": gc.arm_block_size(config, arm),
            "engine": engine,
            "log": ab.parse_log(job_dir / f"worker-{model_id}-{arm}.log"),
            "phases": wsum.get("phases", {}),
            "gdn_state_mib_per_sequence": gb.gdn_page_bytes(config, gc.arm_state_dtype(config, arm))
            * gdn_layers
            / 2**20,
        }
        block, blocks = engine.get("block_size"), engine.get("num_gpu_blocks")
        if block and blocks:
            record["block_tokens"] = int(block)
            record["max_sequences_by_length"] = {
                str(n): gb.max_sequences(int(blocks), n, int(block))
                for n in config["analysis"]["concurrency_lengths"]
            }
        prefill_path = job_dir / f"prefill-{arm}.json"
        if prefill_path.is_file():
            prefill = json.loads(prefill_path.read_text(encoding="utf-8"))
            record["prefill"] = {
                k: prefill.get(k)
                for k in ("sequences", "scored", "stopped", "wall_s", "prompt_tok_per_s")
            } | {
                "engine_block_size": prefill["engine"].get("block_size"),
                "engine_num_gpu_blocks": prefill["engine"].get("num_gpu_blocks"),
                "engine_mamba_ssm_cache_dtype": prefill["engine"].get("mamba_ssm_cache_dtype"),
            }
            record["prefill_log"] = ab.parse_log(job_dir / f"worker-prefill-{model_id}-{arm}.log")
        if (worker / "sequences.json").is_file():
            meta = json.loads((worker / "sequences.json").read_text(encoding="utf-8"))
            record["nonfinite_decode_logprobs"] = sum(
                int(s.get("nonfinite_logprobs", 0)) for s in meta["sequences"]
            )
            record["rollouts"] = ab.rollout_records(worker, answers)
        out.append(record)
    if summary.get("probe"):
        probe = summary["probe"].get("probe") or {}
        out.append(
            {
                "job_dir": job_dir.name,
                "model": model_id,
                "arm": "probe_fp32_b272",
                "smoke": True,
                "probe": probe,
                "log": ab.parse_log(job_dir / f"worker-probe-{model_id}.log"),
            }
        )
    return out


def rollouts_main(args: argparse.Namespace) -> int:
    config = gc.load_config()
    jobs = [rec for d in args.rollout_jobs for rec in rollout_job(Path(d), config)]
    g2.write_json(Path(args.output), {"experiment_id": gc.EXPERIMENT_ID, "jobs": jobs})
    print(json.dumps({"arms": [f"{j['model']}/{j['arm']}" for j in jobs]}))
    return 0


def termination(records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Per arm: how phase R ended; per arm against fp32 and bf16: paired over (prompt, seed),
    which arm's rollout ended (EOS) first. A rollout without EOS (cap or time budget) counts as
    running past every observed EOS; a tie is both ending at one length or neither ending."""

    out: dict[str, Any] = {"arms": {}, "paired": {}}
    for arm, vals in records.items():
        tails = [r["tail_compress_ratio"] for r in vals if r.get("tail_compress_ratio")]
        lengths = [r["completion_len"] for r in vals]
        ended = [r for r in vals if r["finish_reason"] == "stop"]
        out["arms"][arm] = {
            "rollouts": len(vals),
            "ended_eos": len(ended),
            "hit_cap": sum(r["finish_reason"] == "length" for r in vals),
            "cut_at_time_budget": sum(r["finish_reason"] == "cut_at_time_budget" for r in vals),
            "observed_to": max(lengths) if lengths else None,
            "cut_length_min": min(
                (r["completion_len"] for r in vals if r["finish_reason"] == "cut_at_time_budget"),
                default=None,
            ),
            "completion_len_median": float(np.median(lengths)) if lengths else None,
            "completion_len_mean": float(np.mean(lengths)) if lengths else None,
            "ended_before": {str(n): sum(r["completion_len"] < n for r in ended) for n in LENGTHS},
            "boxed_matches_reference": sum(bool(r["boxed_matches_reference"]) for r in vals),
            "boxed_match_share_of_ended": (
                sum(bool(r["boxed_matches_reference"]) for r in ended) / len(ended)
                if ended
                else None
            ),
            "tail_compress_median": float(np.median(tails)) if tails else None,
            "tail_compress_min": float(min(tails)) if tails else None,
        }
    keyed = {
        arm: {(r["prompt_index"], r["seed"]): r for r in vals} for arm, vals in records.items()
    }
    for arm in CONTRAST_ARMS:
        for ref in ("fp32", "bf16"):
            if arm == ref or arm not in keyed or ref not in keyed:
                continue
            shared = sorted(set(keyed[arm]) & set(keyed[ref]))
            arm_longer = ref_longer = 0
            per_prompt: dict[int, int] = {}
            for key in shared:
                x, y = keyed[arm][key], keyed[ref][key]
                x_end = x["completion_len"] if x["finish_reason"] == "stop" else math.inf
                y_end = y["completion_len"] if y["finish_reason"] == "stop" else math.inf
                per_prompt.setdefault(key[0], 0)
                if y_end < x_end:
                    arm_longer += 1
                    per_prompt[key[0]] += 1
                elif x_end < y_end:
                    ref_longer += 1
                    per_prompt[key[0]] -= 1
            wins = sum(v > 0 for v in per_prompt.values())
            losses = sum(v < 0 for v in per_prompt.values())
            out["paired"][f"{arm}_vs_{ref}"] = {
                "pairs": len(shared),
                "arm_ran_longer": arm_longer,
                "ref_ran_longer": ref_longer,
                "neither": len(shared) - arm_longer - ref_longer,
                "sign_test_p": ab.sign_test(arm_longer, ref_longer),
                "prompts_arm_longer": wins,
                "prompts_ref_longer": losses,
                "prompts_tied": len(per_prompt) - wins - losses,
                "prompt_sign_test_p": ab.sign_test(wins, losses),
            }
    return out


def wave_row(phase: dict[str, Any] | None) -> dict[str, Any] | None:
    if not phase or phase.get("status") == "skipped":
        return None
    return {
        k: phase.get(k)
        for k in (
            "output_tok_per_s",
            "wall_s",
            "mean_running",
            "peak_running",
            "preemptions_delta",
            "peak_kv_usage",
            "complete",
        )
    }


# --------------------------------------------------------------------------- report


def fmt(value: Any, digits: int = 4) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "n/a"
    return f"{value:.{digits}f}"


def sci(value: Any) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "n/a"
    return f"{value:+.2e}"


def ci(pair: Any, f: Any = fmt) -> str:
    return f"[{f(pair[0])}, {f(pair[1])}]" if pair else ""


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# g2c-precision-layout-v1 tables (EXPLORATORY)",
        "",
        "fp32 and bf16 are G2b's arms (recomputed from G2b's committed per-token files with the",
        "same code); fp16 and bf16_b528 are this experiment's. d = log p_A - log p_B on each",
        "rollout's own tokens. CIs: 95% bootstrap over the 24 prompts, drawn jointly.",
        "",
    ]
    for model_id, model in result["mismatch"].items():
        lines += [f"## {model_id}", "", "### Rollout vs trainer (dec vs r1), all rollouts", ""]
        lines += [
            "| Arm | Tokens | Mean abs [95% CI] | p99 abs | k3 | Ratios outside [0.8, 1.25] |"
            " Within-sequence slope per 1K [95% CI] | Within sequence x entropy [95% CI] |",
            "|---|---:|---|---:|---:|---:|---|---|",
        ]
        con = model["contrasts"]["dec_vs_r1"]
        for arm in ARMS:
            block = model["subsets"].get(f"{arm}/all", {}).get("dec_vs_r1")
            if not block:
                continue
            c = con.get("arms", {}).get(arm, {})
            lines.append(
                f"| {gc.ARM_LABELS[arm]} | {block['tokens']:,} | {fmt(block['mean_abs'])} "
                f"{ci(c.get('mean_abs', {}).get('ci95'))} | {fmt(block['p99_abs'], 3)} | "
                f"{block['k3']:.2e} | {100 * block['share_ratio_outside_band']:.2f}% | "
                f"{sci(block['slope_within_sequences_per_1k'])} "
                f"{ci(block['slope_within_sequences_ci95'], sci)} | "
                f"{sci(block['slope_within_sequence_entropy_cells_per_1k'])} "
                f"{ci(block['slope_within_sequence_entropy_cells_ci95'], sci)} |"
            )
        lines += ["", "### Arm contrasts (dec vs r1)", ""]
        lines += [
            "| Contrast | Mean abs ratio [95% CI] | k3 ratio [95% CI] | Outside-band ratio |"
            " Within-seq slope diff per 1K [95% CI] |",
            "|---|---|---|---|---|",
        ]
        for name, pair in con.get("pairs", {}).items():
            if name.endswith("excess_fraction"):
                continue
            m, k = pair["mean_abs"], pair["k3"]
            s, o = pair["slope_within_sequences_per_1k"], pair["share_outside_band"]
            two = lambda v: fmt(v, 2)  # noqa: E731
            lines.append(
                f"| {name} | {two(m.get('ratio'))} {ci(m.get('ratio_ci95'), two)}"
                f" | {two(k.get('ratio'))} {ci(k.get('ratio_ci95'), two)} | "
                f"{two(o.get('ratio'))} | {sci(s['diff'])} {ci(s.get('diff_ci95'), sci)} |"
            )
        lines += [
            "",
            "Excess fraction, (arm - fp32) / (bf16 - fp32): 0 is fp32-like, 1 is bf16-like.",
            "",
        ]
        lines += [
            "| Arm | Mean abs [95% CI] | k3 [95% CI] | Within-seq slope [95% CI] |",
            "|---|---|---|---|",
        ]
        for arm in NEW_ARMS:
            ex = con.get("pairs", {}).get(f"{arm}_excess_fraction")
            if not ex:
                continue
            cells = [
                f"{fmt(ex[n]['value'], 3)} {ci(ex[n]['ci95'], lambda v: fmt(v, 3))}"
                for n in ("mean_abs", "k3", "slope_within_sequences_per_1k")
            ]
            lines.append(f"| {arm} | " + " | ".join(cells) + " |")
        lines += ["", "### Which path moved (mean abs)", ""]
        lines += ["| Comparison | " + " | ".join(ARMS) + " |", "|---|" + "---:|" * len(ARMS)]
        for a_key, b_key in COMPARISONS:
            name = f"{a_key}_vs_{b_key}"
            cells = [
                fmt(model["subsets"].get(f"{arm}/all", {}).get(name, {}).get("mean_abs"))
                for arm in ARMS
            ]
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines += ["", "### By position (dec vs r1, mean abs; ratio to fp32 [95% CI])", ""]
        lines += [
            "| Bin start | fp32 | bf16 | fp16 | bf16_b528 | bf16/fp32 | fp16/fp32 |"
            " bf16_b528/fp32 |",
            "|---:|---:|---:|---:|---:|---|---|---|",
        ]
        for row in model["position_ratios"]["dec_vs_r1"]:
            cells = [fmt(row.get(f"{a}_mean_abs")) for a in ARMS]
            ratios = [
                f"{fmt(row.get(f'{a}_over_fp32'), 2)} "
                f"{ci(row.get(f'{a}_over_fp32_ci95'), lambda v: fmt(v, 2))}"
                for a in ARMS[1:]
            ]
            lines.append(f"| {row['start']:,} | " + " | ".join(cells + ratios) + " |")
        lines += ["", "### By r1 entropy (dec vs r1, mean abs; slope per 1K)", ""]
        lines += ["| Entropy (nats) | " + " | ".join(ARMS) + " |", "|---|" + "---|" * len(ARMS)]
        rows: dict[tuple[float, float], dict[str, str]] = {}
        for arm in ARMS:
            block = model["subsets"].get(f"{arm}/all", {}).get("dec_vs_r1") or {}
            for e in block.get("by_entropy", []):
                rows.setdefault((e["entropy_lo"], e["entropy_hi"]), {})[arm] = (
                    f"{fmt(e['mean_abs'], 5)} ({sci(e['slope_per_1k'])})"
                )
        for (lo, hi), cells in sorted(rows.items()):
            label = f"[{lo:g}, {'inf' if hi > 1e8 else f'{hi:g}'})"
            lines.append(f"| {label} | " + " | ".join(cells.get(a, "") for a in ARMS) + " |")
        lines += ["", "### Per seed (dec vs r1 mean abs; within-sequence slope)", ""]
        lines += [
            "| Arm | " + " | ".join(f"seed {s}" for s in (42, 43, 44)) + " |",
            "|---|---|---|---|",
        ]
        for arm in ARMS:
            cells = []
            for s in (42, 43, 44):
                b = model["subsets"].get(f"{arm}/seed_{s}", {}).get("dec_vs_r1")
                cells.append(
                    f"{fmt(b['mean_abs'])} ({sci(b['slope_within_sequences_per_1k'])})" if b else ""
                )
            lines.append(f"| {arm} | " + " | ".join(cells) + " |")
        lines.append("")
    term = result.get("termination", {})
    if term:
        lines += ["## How the rollouts ended (phase R)", ""]
        lines += [
            "| Model | Arm | Rollouts | Ended (EOS) | Hit 32K cap | Cut by time | Median length |"
            " Ended before 8K / 16K / 24K / 28K | Boxed = reference | Tail zlib median |",
            "|---|---|---:|---:|---:|---:|---:|---|---:|---:|",
        ]
        for model_id, model in term.items():
            for arm in ARMS:
                t = model["arms"].get(arm)
                if not t:
                    continue
                eb = t["ended_before"]
                lines.append(
                    f"| {model_id} | {arm} | {t['rollouts']} | {t['ended_eos']} | {t['hit_cap']} "
                    f"| {t['cut_at_time_budget']} | {fmt(t['completion_len_median'], 0)} | "
                    f"{eb['8192']} / {eb['16384']} / {eb['24576']} / {eb['28672']} | "
                    f"{t['boxed_matches_reference']} | {fmt(t['tail_compress_median'], 2)} |"
                )
        lines += ["", "Paired over (prompt, seed): which rollout ended (EOS) first.", ""]
        lines += [
            "| Model | Pair | Arm longer | Reference longer | Neither | Sign test p |"
            " Prompts arm / ref / tied | Prompt sign test p |",
            "|---|---|---:|---:|---:|---:|---|---:|",
        ]
        for model_id, model in term.items():
            for name, p in model["paired"].items():
                lines.append(
                    f"| {model_id} | {name} | {p['arm_ran_longer']} | {p['ref_ran_longer']} | "
                    f"{p['neither']} | {p['sign_test_p']:.2g} | {p['prompts_arm_longer']} / "
                    f"{p['prompts_ref_longer']} / {p['prompts_tied']} | "
                    f"{p['prompt_sign_test_p']:.2g} |"
                )
        lines.append("")
    pool = result.get("block_pool", {})
    if pool:
        lines += ["## Block pool and the seed-42 saturation wave", ""]
        lines += [
            "| Model | Arm | Block (tokens) | Blocks | GDN page padding |"
            " Most 2K / 8K / 32K sequences | Wave tok/s | Mean running | Preemptions | Peak KV |",
            "|---|---|---:|---:|---:|---|---:|---:|---:|---:|",
        ]
        for model_id, model in pool.items():
            for arm in ARMS:
                p = model.get(arm)
                if not p:
                    continue
                w = p.get("wave") or {}
                ms = p.get("max_sequences_by_length") or {}
                kv = w.get("peak_kv_usage")
                kv_text = fmt(100 * kv, 0) if kv is not None else "n/a"
                lines.append(
                    f"| {model_id} | {arm} | {p.get('block_tokens')} | {p.get('num_gpu_blocks')} | "
                    f"{fmt(p.get('mamba_padding_pct'), 2)}% | {ms.get('2048')} / {ms.get('8192')} /"
                    f" {ms.get('32768')} | {fmt(w.get('output_tok_per_s'), 0)} | "
                    f"{fmt(w.get('mean_running'), 0)} | {fmt(w.get('preemptions_delta'), 0)} | "
                    f"{kv_text}% |"
                )
        lines.append("")
    check = result.get("g2b_reproduction")
    if check:
        lines += ["## G2b numbers recomputed against G2b's analysis.json", ""]
        lines += [
            "| Model | Arm | Quantity | Recomputed | G2b committed |",
            "|---|---|---|---:|---:|",
        ]
        for row in check["rows"]:
            lines.append(
                f"| {row['model']} | {row['arm']} | {row['quantity']} | {row['recomputed']:.6g} | "
                f"{row['committed']:.6g} |"
            )
        lines += ["", f"Largest absolute difference: {check['max_abs_diff']:.3g}.", ""]
    return "\n".join(lines) + "\n"


def plot(result: dict[str, Any], output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(3, 3, figsize=(17, 13.5), gridspec_kw={"hspace": 0.45, "wspace": 0.25})
    models = list(result["mismatch"])[:2]

    def line(ax: Any, arm: str, x: Any, y: Any, **kw: Any) -> None:
        st = STYLE[arm]
        ax.plot(x, y, st["ls"], color=st["color"], lw=2, label=st["label"], **kw)

    for col, model_id in enumerate(models):
        model = result["mismatch"][model_id]
        ax = axes[0, col]
        for arm in ARMS:
            block = model["subsets"].get(f"{arm}/all", {}).get("dec_vs_r1")
            rows = [r for r in (block or {}).get("by_position", []) if r["tokens"] >= 200]
            if not rows:
                continue
            x = [r["start"] / 1000 + 0.5 for r in rows]
            line(ax, arm, x, [r["mean_abs"] for r in rows])
            ax.fill_between(
                x,
                [r["mean_abs_ci95"][0] for r in rows],
                [r["mean_abs_ci95"][1] for r in rows],
                color=STYLE[arm]["color"],
                alpha=0.12,
                lw=0,
            )
        ax.set_title(f"{model_id}: rollout vs trainer (dec vs r1) by position")
        ax.set_xlabel("absolute token position (K), 1K bins")
        ax.set_ylabel("mean |Δ log p|")
        ax.grid(alpha=0.25)
        if col == 0:
            ax.legend(fontsize=7.5, loc="upper left", frameon=False)
        # Survival: share of rollouts without EOS yet.
        ax = axes[1, col]
        term = result.get("termination", {}).get(model_id, {})
        for arm in ARMS:
            recs = result.get("rollout_records", {}).get(model_id, {}).get(arm)
            if not recs:
                continue
            ends = sorted(r["completion_len"] for r in recs if r["finish_reason"] == "stop")
            grid = np.arange(0, 32769, 256)
            alive = [1 - sum(e <= g for e in ends) / len(recs) for g in grid]
            line(ax, arm, grid / 1000, alive)
        ax.set_title(f"{model_id}: rollouts with no EOS yet (72 per arm)")
        ax.set_xlabel("completion length (K tokens)")
        ax.set_ylabel("share still running")
        ax.set_ylim(0, 1.02)
        ax.grid(alpha=0.25)
        if term:
            ax.text(
                0.98,
                0.97,
                "\n".join(
                    f"{a}: {term['arms'][a]['ended_eos']} EOS" for a in ARMS if a in term["arms"]
                ),
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=7.5,
                color="#52514e",
            )
        # Entropy bins.
        ax = axes[2, col]
        width = 0.2
        los: list[float] = sorted(
            {
                e["entropy_lo"]
                for arm in ARMS
                for e in (model["subsets"].get(f"{arm}/all", {}).get("dec_vs_r1") or {}).get(
                    "by_entropy", []
                )
            }
        )
        his: dict[float, float] = {}
        for k, arm in enumerate(ARMS):
            block = model["subsets"].get(f"{arm}/all", {}).get("dec_vs_r1") or {}
            ent = block.get("by_entropy", [])
            if not ent:
                continue
            his.update({e["entropy_lo"]: e["entropy_hi"] for e in ent})
            ax.bar(
                [los.index(e["entropy_lo"]) + (k - 1.5) * width for e in ent],
                [e["mean_abs"] for e in ent],
                width * 0.9,
                color=STYLE[arm]["color"],
                hatch="" if STYLE[arm]["ls"] == "-" else "///",
                edgecolor="white",
                label=STYLE[arm]["label"],
            )
        if los:
            labels = [
                f"[{lo:g}, " + ("inf" if his[lo] > 1e8 else f"{his[lo]:g}") + ")" for lo in los
            ]
            ax.set_xticks(np.arange(len(los)), labels)
        ax.set_yscale("log")
        ax.set_title(f"{model_id}: dec vs r1 by r1 entropy (nats); hatched = 272-token blocks")
        ax.set_ylabel("mean |Δ log p| (log scale)")
        ax.grid(alpha=0.25, axis="y")
    # Summary: mean |d| with CIs per arm and model.
    ax = axes[0, 2]
    for m_i, model_id in enumerate(models):
        con = result["mismatch"][model_id]["contrasts"]["dec_vs_r1"].get("arms", {})
        for k, arm in enumerate(ARMS):
            if arm not in con:
                continue
            v = con[arm]["mean_abs"]
            x = m_i * 5 + k
            ax.bar(
                x,
                v["value"],
                0.8,
                color=STYLE[arm]["color"],
                hatch="" if STYLE[arm]["ls"] == "-" else "///",
                edgecolor="white",
            )
            if v["ci95"]:
                ax.errorbar(
                    x,
                    v["value"],
                    yerr=[[v["value"] - v["ci95"][0]], [v["ci95"][1] - v["value"]]],
                    color="#0b0b0b",
                    capsize=3,
                    lw=1,
                )
            ax.text(x, v["value"] * 1.03 + 0.0005, f"{v['value']:.4f}", ha="center", fontsize=7)
    ax.set_xticks([1.5 + 5 * i for i in range(len(models))], models)
    ax.set_ylabel("mean |Δ log p|, dec vs r1 (95% CI over prompts)")
    ax.set_title("All rollouts: fp32, bf16 (G2b), fp16, bf16 at 528-token blocks")
    ax.grid(alpha=0.25, axis="y")
    # Throughput: seed-42 wave per arm.
    ax = axes[1, 2]
    pool = result.get("block_pool", {})
    for m_i, model_id in enumerate(models):
        for k, arm in enumerate(ARMS):
            w = (pool.get(model_id, {}).get(arm) or {}).get("wave") or {}
            if not w.get("output_tok_per_s"):
                continue
            x = m_i * 5 + k
            ax.bar(
                x,
                w["output_tok_per_s"] / 1000,
                0.8,
                color=STYLE[arm]["color"],
                hatch="" if STYLE[arm]["ls"] == "-" else "///",
                edgecolor="white",
            )
            ax.text(
                x, w["output_tok_per_s"] / 1000 + 0.2, f"{w['output_tok_per_s'] / 1000:.1f}K",
                ha="center", fontsize=7,
            )  # fmt: skip
    ax.set_xticks([1.5 + 5 * i for i in range(len(models))], models)
    ax.set_ylabel("output tok/s (K), seed-42 wave, 512 x 2,048 tokens")
    ax.set_title("Saturation wave throughput (one wave per arm)")
    ax.grid(alpha=0.25, axis="y")
    # Which path moved: decode vs r1, prefill vs r1, decode vs prefill.
    ax = axes[2, 2]
    comps = [("dec_vs_r1", "decode vs trainer"), ("pre_vs_r1", "prefill vs trainer"),
             ("dec_vs_pre", "decode vs prefill")]  # fmt: skip
    model_id = models[-1]
    model = result["mismatch"][model_id]
    for c_i, (name, _label) in enumerate(comps):
        for k, arm in enumerate(ARMS):
            block = model["subsets"].get(f"{arm}/all", {}).get(name)
            if not block:
                continue
            ax.bar(
                c_i * 5 + k,
                block["mean_abs"],
                0.8,
                color=STYLE[arm]["color"],
                hatch="" if STYLE[arm]["ls"] == "-" else "///",
                edgecolor="white",
            )
    ax.set_xticks([1.5, 6.5, 11.5], [c[1] for c in comps])
    ax.set_ylabel("mean |Δ log p|")
    ax.set_title(f"{model_id}: which path moved (prefill in each arm's own state and block)")
    ax.grid(alpha=0.25, axis="y")
    fig.suptitle(
        "g2c-precision-layout-v1 (EXPLORATORY): GDN state precision vs block layout in vLLM 0.31.0"
        " (hue = state dtype, solid = 528-token blocks, dashed/hatched = 272-token blocks)",
        fontsize=10,
    )
    fig.savefig(output, dpi=110, bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- analyze


def reproduction_check(
    result: dict[str, Any], g2b_analysis: dict[str, Any] | None
) -> dict[str, Any] | None:
    """G2b's committed dec-vs-r1 numbers against the same quantities recomputed here."""

    if not g2b_analysis:
        return None
    rows = []
    for model_id, model in result["mismatch"].items():
        committed_model = g2b_analysis.get("mismatch", {}).get(model_id)
        if not committed_model:
            continue
        for arm in ("fp32", "bf16"):
            ours = model["subsets"].get(f"{arm}/all", {}).get("dec_vs_r1")
            theirs = committed_model["subsets"].get(f"{arm}/all", {}).get("dec_vs_r1")
            if not ours or not theirs:
                continue
            for q in (
                "tokens",
                "mean_abs",
                "p99_abs",
                "k3",
                "share_ratio_outside_band",
                "slope_within_sequences_per_1k",
                "slope_within_sequence_entropy_cells_per_1k",
            ):
                rows.append(
                    {
                        "model": model_id,
                        "arm": arm,
                        "quantity": q,
                        "recomputed": float(ours[q]),
                        "committed": float(theirs[q]),
                    }
                )
    diffs = [abs(r["recomputed"] - r["committed"]) for r in rows]
    return {"rows": rows, "max_abs_diff": max(diffs) if diffs else float("nan")}


def block_pool(
    g2c_jobs: list[dict[str, Any]], g2b_jobs: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    seed = f"S{config['saturation']['seeds'][0]}"
    attn = gc.attention_page_bytes_per_token(4, 256)
    for job in g2b_jobs + g2c_jobs:
        model_id, arm = job["model"], job["arm"]
        if arm not in ARMS or model_id not in config["models"] or job.get("smoke"):
            continue
        engine = job.get("engine", {})
        dtype = gb.resolved_state_dtype(job.get("state_dtype_setting") or job.get("state_dtype"))
        page = gb.gdn_page_bytes(config, dtype)
        block = job.get("block_tokens") or engine.get("block_size")
        out.setdefault(model_id, {})[arm] = {
            "block_tokens": block,
            "num_gpu_blocks": engine.get("num_gpu_blocks"),
            "mamba_padding_pct": gc.mamba_padding_pct(page, attn, int(block)) if block else None,
            "mamba_padding_pct_logged": (job.get("log") or {}).get("mamba_padding_pct"),
            "max_sequences_by_length": job.get("max_sequences_by_length"),
            "gdn_decode_kernel": (job.get("log") or {}).get("gdn_decode_kernel"),
            "wave": wave_row(job.get("phases", {}).get(seed)),
            "phase_r": {
                k: job.get("phases", {}).get("R", {}).get(k)
                for k in (
                    "wall_s",
                    "output_tok_per_s",
                    "mean_running",
                    "peak_running",
                    "peak_kv_usage",
                )
            },
        }
    return out


def analyze_main(args: argparse.Namespace) -> int:
    config = gc.load_config()
    settings = dict(config["analysis"])
    g2c_files = {}
    for path in args.per_token:
        meta, raw = ab.load_per_token(Path(path))
        g2c_files[meta["model"]] = raw
    g2b_files = {}
    for path in args.g2b_per_token:
        meta, raw = ab.load_per_token(Path(path))
        expected = config["reference"]["per_token_sha256"].get(meta["model"])
        if args.check_g2b_sha256 and g2.sha256_file(Path(path)) != expected:
            raise gc.G2cConfigError(f"{path}: not G2b's per-token file (SHA-256 differs)")
        g2b_files[meta["model"]] = raw
    result: dict[str, Any] = {
        "experiment_id": gc.EXPERIMENT_ID,
        "claim_level": "exploratory",
        "settings": settings,
        "arms": list(ARMS),
        "arm_labels": gc.ARM_LABELS,
        "g2b_per_token_sha256_checked": bool(args.check_g2b_sha256),
        "mismatch": {},
    }
    for model_id in config["models"]:
        if model_id not in g2c_files or model_id not in g2b_files:
            continue
        data = combine(g2b_files[model_id], g2c_files[model_id])
        result["mismatch"][model_id] = analyze_model(data, settings)
        nonfinite = g2c_files[model_id].get("nonfinite_decode")
        result["mismatch"][model_id]["nonfinite_decode_logprobs"] = (
            int(nonfinite.sum()) if nonfinite is not None else None
        )
    g2c_jobs = (
        json.loads(Path(args.rollouts).read_text(encoding="utf-8"))["jobs"] if args.rollouts else []
    )
    g2b_jobs = (
        json.loads(Path(args.g2b_throughput).read_text(encoding="utf-8"))["jobs"]
        if args.g2b_throughput
        else []
    )
    records: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for job in g2b_jobs + g2c_jobs:
        if job.get("smoke") or job["arm"] not in ARMS or job["model"] not in config["models"]:
            continue
        if job.get("rollouts"):
            records.setdefault(job["model"], {})[job["arm"]] = job["rollouts"]
    result["rollout_records"] = records
    result["termination"] = {m: termination(r) for m, r in records.items()}
    result["block_pool"] = block_pool(g2c_jobs, g2b_jobs, config)
    result["probe"] = [j for j in g2c_jobs if j["arm"] == "probe_fp32_b272"]
    if args.g2b_analysis:
        committed = json.loads(Path(args.g2b_analysis).read_text(encoding="utf-8"))
        result["g2b_reproduction"] = reproduction_check(result, committed)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    g2.write_json(out / "analysis.json", result)
    (out / "tables.md").write_text(markdown(result), encoding="utf-8")
    plot(result, out / "g2c-precision-vs-layout.png")
    print(json.dumps({"written": ["analysis.json", "tables.md", "g2c-precision-vs-layout.png"]}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("pack", allow_abbrev=False)
    pack.add_argument("--model", required=True)
    pack.add_argument("--rollouts", required=True)
    pack.add_argument("--teacher-force", required=True)
    pack.add_argument("--output", required=True)
    roll = sub.add_parser("rollouts", allow_abbrev=False)
    roll.add_argument("--rollout-jobs", nargs="+", required=True)
    roll.add_argument("--output", required=True)
    an = sub.add_parser("analyze", allow_abbrev=False)
    an.add_argument("--per-token", nargs="+", required=True)
    an.add_argument("--g2b-per-token", nargs="+", required=True)
    an.add_argument("--check-g2b-sha256", action="store_true")
    an.add_argument("--rollouts", default=None)
    an.add_argument("--g2b-throughput", default=None)
    an.add_argument("--g2b-analysis", default=None)
    an.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    return {"pack": pack_main, "rollouts": rollouts_main, "analyze": analyze_main}[args.command](
        args
    )


if __name__ == "__main__":
    sys.exit(main())
