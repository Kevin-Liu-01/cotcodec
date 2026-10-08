"""Check the revealed audit salt: its digest and every sample item id.

Run from the repository root with it on the path (the harness is unchanged since 65bc2e2):

    PYTHONPATH=. python program/evidence/2026-10-08/q2-mutation-confirm/audit/salt_check.py
"""

from __future__ import annotations

import json
from pathlib import Path

from harness.q2_mutation import raters

HERE = Path(__file__).resolve().parent
COMMITTED = "194ee66ccc11f93c16bffdc7cf54d0b0f5398f35cbdb3541bb9d9d511c40451e"


def main() -> None:
    salt = raters.check_salt((HERE / "salt.hex").read_text(encoding="ascii").strip())
    rows = [
        json.loads(line)
        for line in (HERE / "released/confirm-audit-v1/sample.jsonl").read_text().splitlines()
        if line.strip()
    ]
    recomputed = [r for r in rows if raters.opaque_item_id(r["mutant_id"], salt) == r["item_id"]]
    manifest = json.loads((HERE / "isolated-export/iso-manifest.json").read_text())
    redacted = json.loads((HERE / "sample/sample-summary.redacted.json").read_text())
    result = {
        "schema": "q2m-confirm-salt-check-v1",
        "salt_sha256": raters.salt_sha256(salt),
        "committed_salt_sha256": COMMITTED,
        "redacted_summary_salt_sha256": redacted["salt_sha256"],
        "digest_matches": raters.salt_sha256(salt) == COMMITTED == redacted["salt_sha256"],
        "sample_items": len(rows),
        "item_ids_recomputed": len(recomputed),
        "sample_ids_equal_export_ids": {r["item_id"] for r in rows} == set(manifest["items"]),
        "rule": "raters.opaque_item_id: first 16 hex of SHA-256('q2-audit:{salt}:{key}') (D34)",
    }
    (HERE / "salt-check.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
