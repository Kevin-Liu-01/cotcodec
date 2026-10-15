#!/usr/bin/env python3
"""Write the seed-42 sequences of a g2c per-token file (exact rows, same format) for the repo.

Usage: subset_per_token.py <per-token.npz> <out.npz> [seed]. Per-sequence arrays are sliced by
sequence, per-token arrays by the kept sequences' token ranges; offsets are rebuilt (G2b's
ops/subset_per_token.py without the pairing fields, which this format does not have).
"""

import json
import sys

import numpy as np

SEQ_KEYS = ("prompt_len", "arm", "seed", "prompt_index", "finished", "nonfinite_decode")


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    raw = np.load(src)
    offsets = raw["offsets"]
    keep = np.nonzero(raw["seed"] == seed)[0]
    lengths = np.diff(offsets)[keep]
    token_index = np.concatenate([np.arange(offsets[i], offsets[i + 1]) for i in keep])
    out = {"offsets": np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)}
    for name in raw.files:
        if name in ("offsets", "meta_json"):
            continue
        out[name] = raw[name][keep] if name in SEQ_KEYS else raw[name][token_index]
    meta = json.loads(bytes(raw["meta_json"]).decode())
    meta.update(
        subset=f"seed {seed} sequences only (exact rows)",
        sequences=int(len(keep)),
        tokens=int(out["offsets"][-1]),
    )
    out["meta_json"] = np.frombuffer(json.dumps(meta, sort_keys=True).encode(), dtype=np.uint8)
    np.savez_compressed(dst, **out)
    print(json.dumps(meta, sort_keys=True))


if __name__ == "__main__":
    main()
