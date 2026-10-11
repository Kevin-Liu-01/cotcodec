#!/usr/bin/env python3
"""Merge S1v2 per-process outputs into the bundle's JSON files, with each input's SHA-256.

Usage:
  merge_v2.py calib <out.json> <part files...>     # error-model calibration table
  merge_v2.py part <key> <out.json> <part files...>  # atten | ident | gates | linem | oc
"""
import hashlib
import json
import sys
from pathlib import Path


def load(p):
    b = Path(p).read_bytes()
    return json.loads(b), hashlib.sha256(b).hexdigest()


def main():
    mode = sys.argv[1]
    if mode == "calib":
        out, files = Path(sys.argv[2]), sys.argv[3:]
        table, inputs, seed, pairs, splits = {}, [], None, None, None
        for f in files:
            d, h = load(f)
            c = d["calib"]
            seed, pairs, splits = c["seed"], c["pairs"], c["splits_spurious_to_missed"]
            for prof, v in c["table"].items():
                table.setdefault(prof, {}).update(v)
            inputs.append({"file": Path(f).name, "sha256": h, "argv": d["argv"], "elapsed_seconds": d["elapsed_seconds"]})
        res = {"script": "instrument_sim_v2.py --part calib", "calib": {"seed": seed, "pairs": pairs,
               "splits_spurious_to_missed": splits, "table": table}, "inputs": inputs}
    else:
        key, out, files = sys.argv[2], Path(sys.argv[3]), sys.argv[4:]
        items, inputs = [], []
        for f in sorted(files):
            d, h = load(f)
            for it in d[key]:
                it = dict(it)
                it["_source"] = Path(f).name
                items.append(it)
            inputs.append({"file": Path(f).name, "sha256": h, "argv": d["argv"], "elapsed_seconds": d["elapsed_seconds"],
                           "estimator_constants": d.get("estimator_constants")})
        res = {"script": f"instrument_sim_v2.py --part {key}", key: items, "inputs": inputs}
    out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(out, len(res.get(sys.argv[2], [])) if mode != "calib" else "calib")


if __name__ == "__main__":
    main()
