"""Freeze-simulation text rewrites for q3-dense-headroom-precheck-v2 (scratch clones only).

Usage: rewrite.py CLONE MODE, MODE one of:
  full        the registered step 1: status paragraph and design-decision lead-in rewritten to the
              frozen wording, naming D42 (the real decision in program/decisions.md; no stand-in)
  status-only only the status paragraph rewritten; the lead-in keeps its draft wording
  wrong-dec   both rewritten but naming D41, which neither names this experiment nor amends D36 (iii)
"""
import sys
from pathlib import Path

clone, mode = Path(sys.argv[1]), sys.argv[2]
reg = clone / "program/preregistrations/q3-dense-headroom-precheck-v2.md"
text = reg.read_text()
dec = "D41" if mode == "wrong-dec" else "D42"

start = text.index("Status: DRAFT, not frozen.")
end = text.index("\n\n", start)
status = (
    "Status: frozen in program/preregistrations/ledger.jsonl; see the ledger row\n"
    "for the freeze time and `git_head_at_freeze`. FREEZE SIMULATION ONLY (scratch\n"
    "clone). The design is v1's (`q3-dense-headroom-precheck-v1`, frozen 2026-10-08\n"
    "after D32), kept unchanged by program decision D36 (`program/decisions.md`).\n"
    "The repairs and limits listed under \"Changes from v1 (D36)\" and design\n"
    f"decisions 16-21 were accepted in {dec}, as amended by it, after a narrow\n"
    f"re-check of the measured limits; {dec} amends D36 (iii) for the\n"
    "Qwen3.5-4B-Base lane (decision 18) and authorised the second development\n"
    "timing job, whose measurement of the fixed path (Slurm 810) sets the 4B limit\n"
    "by D36's rule (decisions 20 and 21). No lane job of this experiment ran before\n"
    "the freeze; every lane job verifies this file's digest against its ledger row\n"
    "at start-up and refuses code whose SHA-256 differs from the table below. Both\n"
    "development timing jobs ran before the freeze (Compute): Slurm 766 on the 4B\n"
    "path as it was before the fix (cuDNN's attention on) and Slurm 810 on the\n"
    "fixed path (cuDNN's attention off).")
text = text[:start] + status + text[end:]

if mode in ("full", "wrong-dec"):
    old = ("Decisions 16-21 are v2's (D36). D42 accepts them as amended by it, after a\n"
           "narrow re-check of the measured limits that is still to be done: decision\n"
           "18's switch departs from D36 (iii) on the 4B lane, which D42 (i) amends, and\n"
           "decisions 20 and 21 set the 4B limit from the second timing job that D42 (ii)\n"
           "authorised (Freeze procedure, step 1).")
    new = (f"Decisions 16-21 are v2's (D36), accepted in {dec} as amended by it, after a\n"
           "narrow re-check of the measured limits: decision 18's switch departs from\n"
           f"D36 (iii) on the 4B lane, which {dec} (i) amends, and decisions 20 and 21 set\n"
           f"the 4B limit from the second timing job that {dec} (ii) authorised.")
    assert text.count(old) == 1
    text = text.replace(old, new)
reg.write_text(text)
print(mode, "rewritten with", dec)
