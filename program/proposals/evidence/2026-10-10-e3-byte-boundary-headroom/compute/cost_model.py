#!/usr/bin/env python3
"""S2: GPU-hour estimate and registered caps for the E3 Stage-0 probe (arithmetic only).

No throughput for H-Net or for the aligners has been measured on this host, so
every number below is an assumption stated with its source. Caps are counted
under D22: the sum of registered caps of every job, never expected use.

Usage: cost_model.py <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# FLORES+ dev (997) + devtest (1012) sentences per language; bytes per sentence are the
# asset cell's estimates (FLORES+ is gated and was not downloaded): EN 130, ZH 125, KO 140, PL 140.
SENTENCES = 997 + 1012
BYTES_PER_SENTENCE = {"eng_Latn": 130, "cmn_Hans": 125, "kor_Hang": 140, "pol_Latn": 140}
HIGH_BYTES_FACTOR = 1.5

# Checkpoints read on the GPU (parameter counts: arXiv 2507.07955 Table 1 for the XL models;
# the Chinese model's count is inferred from its 7.02 GB fp32 file, 4 bytes per parameter).
CHECKPOINTS = {
    "cartesia-ai/hnet_2stage_XL": {"params": 1.6e9, "file_gb": 6.41, "role": "English learned boundaries (decision arm, EN side)"},
    "cartesia-ai/hnet_2stage_XL_chinese": {"params": 7.02e9 / 4, "file_gb": 7.02, "role": "Chinese learned boundaries (decision arm, ZH side)"},
    "cartesia-ai/hnet_1stage_XL": {"params": 1.3e9, "file_gb": 5.08, "role": "English 1-stage boundaries (descriptive arm)"},
}
# Upper bound: every parameter touched at every byte (2 FLOPs per parameter per byte).
# Central: one third of that (H-Net's main network runs at chunk rate, not byte rate).
CENTRAL_FLOP_FRACTION = 1 / 3

# Effective throughput (fp32, TF32 disabled for the boundary computation, small batches):
# assumptions, not measurements. H100 SXM fp32 non-tensor peak is about 67 TFLOPS (NVIDIA datasheet).
EFFECTIVE_TFLOPS = {"central": 30.0, "high": 20.0}

OVERHEAD_MIN = {
    "container_start_and_env_check": {"central": 3.0, "high": 4.0},
    "per_checkpoint_load_and_kernel_jit": {"central": 2.5, "high": 4.0},
    "aligners_two_models_6027_pairs": {"central": 2.0, "high": 3.0},
    "hashing_and_writing": {"central": 1.5, "high": 2.0},
}

SMOKE_CAP = 0.20
PROBE_CAP = 0.60
CAP_FORMULA_FACTOR = 1.05  # the probe cap must exceed the high estimate by at least 5%


def main() -> int:
    out = Path(sys.argv[1])
    bytes_central = SENTENCES * sum(BYTES_PER_SENTENCE.values())
    bytes_high = bytes_central * HIGH_BYTES_FACTOR
    flop_per_byte_upper = sum(2 * c["params"] for c in CHECKPOINTS.values())
    result = {"assumptions": {
        "sentences_per_language": SENTENCES, "bytes_per_sentence_estimate": BYTES_PER_SENTENCE,
        "high_bytes_factor": HIGH_BYTES_FACTOR, "checkpoints": CHECKPOINTS,
        "central_flop_fraction_of_upper_bound": CENTRAL_FLOP_FRACTION, "effective_tflops": EFFECTIVE_TFLOPS,
        "overhead_minutes": OVERHEAD_MIN,
        "measured_on_host": "nothing: no H-Net, Bolmo or aligner throughput exists on this host"}}
    rows = {}
    for case in ("central", "high"):
        nbytes = bytes_central if case == "central" else bytes_high
        flops = nbytes * flop_per_byte_upper * (CENTRAL_FLOP_FRACTION if case == "central" else 1.0)
        compute_min = flops / (EFFECTIVE_TFLOPS[case] * 1e12) / 60
        overhead = (OVERHEAD_MIN["container_start_and_env_check"][case]
                    + len(CHECKPOINTS) * OVERHEAD_MIN["per_checkpoint_load_and_kernel_jit"][case]
                    + OVERHEAD_MIN["aligners_two_models_6027_pairs"][case]
                    + OVERHEAD_MIN["hashing_and_writing"][case])
        total_min = compute_min + overhead
        rows[case] = {"bytes": round(nbytes), "flops": f"{flops:.3e}", "compute_minutes": round(compute_min, 2),
                      "overhead_minutes": round(overhead, 2), "total_minutes": round(total_min, 2),
                      "gpu_hours_one_gpu": round(total_min / 60, 3)}
    high = rows["high"]["gpu_hours_one_gpu"]
    result["estimate"] = rows
    result["caps"] = {
        "smoke_job_cap_gpu_h": SMOKE_CAP,
        "smoke_job_scope": "one GPU: imports, weights_only load of all three checkpoints, one forward of the 2-stage XL model on 64 synthetic byte strings (no FLORES text), a determinism check (two runs bit-identical), and a kill-and-resume check of the per-checkpoint output files",
        "probe_job_cap_gpu_h": PROBE_CAP,
        "probe_cap_over_high_estimate": round(PROBE_CAP / high, 3),
        "probe_cap_rule": f"cap >= {CAP_FORMULA_FACTOR} x high estimate: {PROBE_CAP} >= {round(CAP_FORMULA_FACTOR * high, 3)}",
        "sum_of_caps_gpu_h": round(SMOKE_CAP + PROBE_CAP, 2),
        "d22_counting": "sum of registered caps of every job whatever its outcome; the overlay image build is a host CPU job (0 GPU-h); CPU analysis runs on the development Mac (0 GPU-h)",
        "threshold_gpu_h": 8.0,
        "under_threshold": SMOKE_CAP + PROBE_CAP <= 8.0,
    }
    result["cpu_analysis_estimate"] = {
        "pbd_scoring": "6,027 sentence pairs x about 26 boundary systems x 2 aligners x about 5 ms = about 26 CPU-minutes (NumPy; measured order of magnitude from compute/instrument_sim.py on the development Mac under load average 40-85)",
        "uot_secondary": "300 devtest pairs per language x 10 systems x 6 evaluator calls x about 0.27 s (one call measured at 0.266 s under load average about 85) = about 4.0 CPU-hours, about 30 minutes on 8 processes",
        "bootstrap": "B = 2,000 sentence-cluster resamples of per-sentence counts: seconds",
    }
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: rows[k]["gpu_hours_one_gpu"] for k in rows}), result["caps"]["sum_of_caps_gpu_h"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
