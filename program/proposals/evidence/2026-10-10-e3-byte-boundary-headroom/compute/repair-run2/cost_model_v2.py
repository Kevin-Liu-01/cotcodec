#!/usr/bin/env python3
"""S2v2: GPU-hour estimate and registered caps for e3-byte-boundary-headroom-v2 (arithmetic only).

Changes from wave 1's S2 (../cost_model.py, kept as it was):
* bf16, the checkpoints' native dtype (upstream generate.py builds the model in bf16;
  hnet/modules/mha.py asserts fp16 or bf16 for flash attention), instead of fp32;
* encoder-only extraction: stage-1 scores need the outer encoder and the stage-1 router;
  stage-2 scores need the stage-1 chunking, the inner encoder (one attention layer and
  four Mamba-2 layers in the 2-stage XL layout) and the stage-2 router. The main network
  (27 attention layers) and the decoders are never run. The central case counts only
  the encoders; the high case still counts every parameter at every byte, as if the
  split failed and the full forward had to run;
* aligners: OmniAlign (one encoder pass per side) and BinaryAlign (one mDeBERTa-v3-base
  pass per source word), both on GPU in the probe job, plus the 300-pair gold set if
  reserved sign-off R5 is granted.
No throughput has been measured on this host; every number is an assumption with its
source. Caps are counted under D22: the sum of registered caps of every job.

Usage: cost_model_v2.py <out.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SENTENCES = 997 + 1012                      # FLORES+ dev + devtest, per language
BYTES_PER_SENTENCE = {"eng_Latn": 130, "cmn_Hans": 125, "kor_Hang": 140, "pol_Latn": 140}  # wave-1 asset cell estimate
WORDS_PER_SENTENCE_EN = 25                  # S1v2 synthetic English side 25.5 words; FLORES+ not downloaded
HIGH_BYTES_FACTOR = 1.5

CHECKPOINTS = {  # parameter counts as in wave 1 (2507.07955 Table 1; Chinese inferred from file size)
    "cartesia-ai/hnet_2stage_XL": {"params": 1.6e9, "encoder_fraction": 0.06},
    "cartesia-ai/hnet_2stage_XL_chinese": {"params": 1.755e9, "encoder_fraction": 0.06},
    "cartesia-ai/hnet_1stage_XL": {"params": 1.3e9, "encoder_fraction": 0.05},
}
# encoder_fraction: share of parameters in the outer and inner encoders plus routers, an
# assumption from the layouts (m4 outer encoder at d_model[0], T1m4 inner encoder at
# d_model[1], against T27 main networks); the high case ignores it.
EFFECTIVE_TFLOPS = {"central": 30.0, "high": 20.0}   # wave 1's fp32 assumption kept for bf16 (conservative: bf16 tensor cores are faster)

ALIGNER_PAIRS = 3 * SENTENCES + 300          # OmniAlign: EN-ZH, EN-KO, EN-PL on dev and devtest, plus the optional gold set
BINARYALIGN_PAIRS = SENTENCES + 300          # BinaryAlign (zhen checkpoint): EN-ZH dev and devtest, plus the optional gold set
BINARYALIGN = {"params": 2.8e8, "tokens_per_pass": 90}   # mDeBERTa-v3-base; one pass per source word
OMNIALIGN = {"params": 3.05e8, "tokens_per_pass": 80}    # mGTE base; two passes per pair

OVERHEAD_MIN = {
    "container_start_and_env_check": {"central": 3.0, "high": 4.0},
    "per_checkpoint_load_and_kernel_jit": {"central": 2.5, "high": 4.0},   # three H-Net checkpoints
    "aligner_model_loads": {"central": 1.5, "high": 3.0},
    "hashing_and_writing": {"central": 1.5, "high": 2.0},
}

SMOKE_CAP = 0.20
PROBE_CAP = 0.70
CAP_FORMULA_FACTOR = 1.05


def main() -> int:
    out = Path(sys.argv[1])
    bytes_central = SENTENCES * sum(BYTES_PER_SENTENCE.values())
    rows = {}
    for case in ("central", "high"):
        nbytes = bytes_central * (HIGH_BYTES_FACTOR if case == "high" else 1.0)
        per_byte = sum(2 * c["params"] * (c["encoder_fraction"] if case == "central" else 1.0)
                       for c in CHECKPOINTS.values())
        hnet_flops = nbytes * per_byte
        words = BINARYALIGN_PAIRS * WORDS_PER_SENTENCE_EN * (1.5 if case == "high" else 1.0)
        bin_flops = words * 2 * BINARYALIGN["params"] * BINARYALIGN["tokens_per_pass"]
        omni_flops = ALIGNER_PAIRS * 2 * 2 * OMNIALIGN["params"] * OMNIALIGN["tokens_per_pass"]
        flops = hnet_flops + bin_flops + omni_flops
        compute_min = flops / (EFFECTIVE_TFLOPS[case] * 1e12) / 60
        overhead = (OVERHEAD_MIN["container_start_and_env_check"][case]
                    + len(CHECKPOINTS) * OVERHEAD_MIN["per_checkpoint_load_and_kernel_jit"][case]
                    + OVERHEAD_MIN["aligner_model_loads"][case]
                    + OVERHEAD_MIN["hashing_and_writing"][case])
        total = compute_min + overhead
        rows[case] = {"bytes": round(nbytes), "hnet_flops": f"{hnet_flops:.3e}", "binaryalign_flops": f"{bin_flops:.3e}",
                      "omnialign_flops": f"{omni_flops:.3e}", "compute_minutes": round(compute_min, 2),
                      "overhead_minutes": round(overhead, 2), "total_minutes": round(total, 2),
                      "gpu_hours_one_gpu": round(total / 60, 3)}
    high = rows["high"]["gpu_hours_one_gpu"]
    result = {
        "assumptions": {"sentences_per_language": SENTENCES, "bytes_per_sentence_estimate": BYTES_PER_SENTENCE,
                        "english_words_per_sentence": WORDS_PER_SENTENCE_EN, "checkpoints": CHECKPOINTS,
                        "effective_tflops_bf16": EFFECTIVE_TFLOPS, "aligner_pairs_omnialign": ALIGNER_PAIRS, "aligner_pairs_binaryalign": BINARYALIGN_PAIRS,
                        "binaryalign": BINARYALIGN, "omnialign": OMNIALIGN, "overhead_minutes": OVERHEAD_MIN,
                        "measured_on_host": "nothing: no H-Net or aligner throughput exists on this host"},
        "estimate": rows,
        "caps": {"smoke_job_cap_gpu_h": SMOKE_CAP,
                 "smoke_job_scope": "one GPU: imports in the v2 overlay, weights_only loads of the three checkpoints, encoder-only stage-1 and stage-2 extraction of the 2-stage XL model on 64 synthetic byte strings (no FLORES text), the same extraction checked against a full upstream forward's boundary outputs on those strings, two runs bit-identical, a kill-and-resume of per-checkpoint files, and both aligners on 8 synthetic sentence pairs",
                 "probe_job_cap_gpu_h": PROBE_CAP,
                 "probe_cap_over_high_estimate": round(PROBE_CAP / high, 3),
                 "probe_cap_rule": f"cap >= {CAP_FORMULA_FACTOR} x high estimate: {PROBE_CAP} >= {round(CAP_FORMULA_FACTOR * high, 3)}",
                 "probe_cap_rule_met": PROBE_CAP >= CAP_FORMULA_FACTOR * high,
                 "sum_of_caps_gpu_h": round(SMOKE_CAP + PROBE_CAP, 2),
                 "d22_counting": "sum of registered caps of every job whatever its outcome; the overlay build and the downloads are host CPU jobs (0 GPU-h); segmentation, parsing and scoring run on CPU (0 GPU-h)",
                 "threshold_gpu_h": 8.0, "under_threshold": SMOKE_CAP + PROBE_CAP <= 8.0},
        "cpu_analysis_estimate": {
            "segmentation_and_parsing": "spaCy small pipelines on 2,009 sentences x 4 languages: minutes on one core",
            "scoring": "allowed pairs about 7 ms, floor (64 draws) about 6 ms per sentence and aligner on the development Mac (S1v2, measured under load); 6,027 pairs x 2 aligners x (7 + 6) ms plus about 20 systems x 1 ms: under 5 CPU-minutes",
            "bootstrap": "B = 2,000 document-cluster resamples of per-sentence counts: seconds"},
    }
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: rows[k]["gpu_hours_one_gpu"] for k in rows}), result["caps"]["sum_of_caps_gpu_h"], result["caps"]["probe_cap_rule_met"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
