#!/usr/bin/env python3
"""Write the seed-42 sequences of a g2b per-token file (exact rows, same format) for the repo.

Usage: subset_per_token.py <per-token.npz> <out.npz> [seed]. Per-sequence arrays are sliced by
sequence, per-token arrays by the kept sequences' token ranges; offsets are rebuilt. The
partner index is remapped (or -1 when the partner is not kept).
"""

import json
import sys

import numpy as np

SEQ_KEYS = ("prompt_len", "arm", "seed", "prompt_index", "finished", "pack_id", "pack_slot",
            "partner", "common_prefix")


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 42
    raw = np.load(src)
    offsets = raw["offsets"]
    keep = np.nonzero(raw["seed"] == seed)[0]
    remap = np.full(len(raw["seed"]), -1, dtype=np.int32)
    remap[keep] = np.arange(len(keep), dtype=np.int32)
    lengths = np.diff(offsets)[keep]
    token_index = np.concatenate([np.arange(offsets[i], offsets[i + 1]) for i in keep])
    out = {"offsets": np.concatenate([[0], np.cumsum(lengths)]).astype(np.int64)}
    for name in raw.files:
        if name in ("offsets", "meta_json"):
            continue
        if name in SEQ_KEYS:
            out[name] = raw[name][keep]
        else:
            out[name] = raw[name][token_index]
    out["partner"] = np.where(out["partner"] >= 0, remap[np.maximum(out["partner"], 0)], -1).astype(np.int32)
    meta = json.loads(bytes(raw["meta_json"]).decode())
    meta.update(subset=f"seed {seed} sequences only (exact rows)", sequences=int(len(keep)),
                tokens=int(out["offsets"][-1]))
    out["meta_json"] = np.frombuffer(json.dumps(meta, sort_keys=True).encode(), dtype=np.uint8)
    np.savez_compressed(dst, **out)
    print(json.dumps(meta, sort_keys=True))


if __name__ == "__main__":
    main()
