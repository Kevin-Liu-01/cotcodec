"""Fail unless the 'after' dpkg state only adds packages to the 'before' state."""

import json
import sys


def load(path: str) -> dict[str, tuple[str, str]]:
    rows = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            name, version, status = line.rstrip("\n").split("\t")
            rows[name] = (version, status)
    return rows


before, after = load(sys.argv[1]), load(sys.argv[2])
changed = {
    name: {"before": before[name][0], "after": after.get(name, ("REMOVED", ""))[0]}
    for name in before
    if before[name][1].endswith("installed")
    and (name not in after or after[name][0] != before[name][0])
}
added = {
    name: after[name][0]
    for name in after
    if after[name][1].endswith("installed")
    and (name not in before or not before[name][1].endswith("installed"))
}
print(json.dumps({"changed": changed, "added": added}, indent=1, sort_keys=True))
if changed:
    sys.exit(f"pre-existing VM packages changed: {sorted(changed)}")
