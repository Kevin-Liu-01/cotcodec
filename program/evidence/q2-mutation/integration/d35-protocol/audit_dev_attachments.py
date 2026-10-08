"""Rerun the registered transcript audit over copies of the D34 dev transcripts.

Usage: ``python audit_dev_attachments.py <dir with q2m-d34/iso-v5-manifest.json>
<dir with tdone/ and tint/>`` from the repository root. ``tdone/`` holds the
142 answering agents' transcripts (``{item}.jsonl``), ``tint/`` the 16
interrupted attempts (``{item}.{agent}.jsonl``). Prints the void reasons (the
answer-only reasons dropped for interrupted attempts, as ``ingest_isolated``
does), the count of every attachment type, the types outside
``rater_runner.HARNESS_ATTACHMENT_TYPES`` and the relay-frame digests.
Transcripts quote document text and are never committed; this prints counts.
"""

import collections
import json
import sys
from pathlib import Path

from harness.q2_mutation import rater_runner as rr

S = Path(sys.argv[1])
R = Path(sys.argv[2])
m = json.loads((S / "q2m-d34/iso-v5-manifest.json").read_text())
ids = list(m["items"])
voids: collections.Counter[str] = collections.Counter()
att: collections.Counter[str] = collections.Counter()
relays: collections.Counter[str] = collections.Counter()
n = 0
for d in (R / "tdone", R / "tint"):
    for f in sorted(d.glob("*.jsonl")):
        item = f.name.split(".")[0]
        entry = m["items"][item]
        expected = rr.render_isolated_prompt(f"{m['iso_root']}/{entry['dir']}", item)
        res = rr.audit_transcript(
            f.read_bytes(),
            Path(m["iso_root"]) / entry["dir"],
            item_id=item,
            expected_prompt=expected,
            item_ids=ids,
        )
        n += 1
        reasons = res["void_reasons"]
        if d.name == "tint":
            reasons = [r for r in reasons if r not in rr.ANSWER_ONLY_REASONS]
        voids.update(reasons)
        att.update(res["attachment_types"])
        relays.update(res["relay_frames_sha256"])
print(
    json.dumps(
        {
            "transcripts": n,
            "void_reasons": dict(voids),
            "attachments": sum(att.values()),
            "attachment_types": dict(sorted(att.items())),
            "types_outside_registry": sorted(set(att) - rr.HARNESS_ATTACHMENT_TYPES),
            "registry_unseen": sorted(rr.HARNESS_ATTACHMENT_TYPES - set(att)),
            "relay_frames": {k[:8]: v for k, v in relays.items()},
        },
        indent=1,
    )
)
