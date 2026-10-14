"""addreadme.py ROWFILE NOTEFILE: append a jobs-table row after the table's last job row and a
per-job note at the end of the per-job notes (before the stint-1 stop section)."""
import re, sys
p = "/Users/kevinliu/repos/cotcodec-wt-ops-s2v5/program/evidence/2026-10-14/s2v5-phase0-run/README.md"
s = open(p).read()
row = open(sys.argv[1]).read().strip("\n")
note = open(sys.argv[2]).read().strip("\n")
lines = s.split("\n")
idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1[0-9]{3} \| K1 ", l))
lines.insert(idx + 1, row)
s = "\n".join(lines)
anchor = "\n\n## Stint 1 stop"
assert s.count(anchor) == 1
s = s.replace(anchor, "\n" + note + anchor, 1)
open(p, "w").write(s)
