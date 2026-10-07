"""Print a JSON fingerprint of the running interpreter's installed distributions.

For each distribution: name, version and the SHA-256 of its RECORD file (which
lists every installed file with its own hash). The overall digest is over the
sorted (name, version, record_sha256) triples, so two venvs with the same
digest hold byte-identical installed files.
"""

import hashlib
import json
import platform
import sys
from importlib import metadata

rows = []
for dist in metadata.distributions():
    record = dist.read_text("RECORD") or ""
    rows.append(
        {
            "name": dist.metadata["Name"],
            "version": dist.version,
            "record_sha256": hashlib.sha256(record.encode("utf-8")).hexdigest(),
        }
    )
rows.sort(key=lambda row: (row["name"].lower(), row["version"]))
digest = hashlib.sha256(
    json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
print(
    json.dumps(
        {
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "n_distributions": len(rows),
            "fingerprint_sha256": digest,
            "distributions": rows,
        },
        indent=1,
    )
)
