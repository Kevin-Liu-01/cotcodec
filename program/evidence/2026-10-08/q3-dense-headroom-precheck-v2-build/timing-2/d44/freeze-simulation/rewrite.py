"""Freeze-simulation text rewrites for q3-dense-headroom-precheck-v2 after D44 (scratch clones only).

Usage: rewrite.py CLONE MODE, MODE one of:
  full        the registered step 1: status paragraph and design-decision lead-in rewritten to the
              frozen wording, naming D42 and D44 (the real decisions in program/decisions.md)
  status-only only the status paragraph rewritten; the lead-in keeps its draft wording
  wrong-dec   both rewritten, naming D41 (which neither names this experiment nor amends D36 (iii))
              in place of D42, and D44
  d42-only    both rewritten to the wording used before D44, naming D42 only
"""
import sys
import textwrap
from pathlib import Path

clone, mode = Path(sys.argv[1]), sys.argv[2]
assert mode in ("full", "status-only", "wrong-dec", "d42-only"), mode
reg = clone / "program/preregistrations/q3-dense-headroom-precheck-v2.md"
text = reg.read_text()
a = "D41" if mode == "wrong-dec" else "D42"
with_d44 = mode != "d42-only"

if with_d44:
    accepted = f"were accepted in {a} and D44, as amended by them, after a narrow re-check of the measured limits;"
    tail = ("; D44 closed the re-check and set that limit at 32 minutes, the largest of the estimates "
            "computed from the measurement.")
else:
    accepted = f"were accepted in {a}, as amended by it, after a narrow re-check of the measured limits;"
    tail = "."
start = text.index("Status: DRAFT, not frozen.")
end = text.index("\n\n", start)
status = (
    "Status: frozen in program/preregistrations/ledger.jsonl; see the ledger row\n"
    "for the freeze time and `git_head_at_freeze`. FREEZE SIMULATION ONLY (scratch\n"
    "clone). The design is v1's (`q3-dense-headroom-precheck-v1`, frozen 2026-10-08\n"
    "after D32), kept unchanged by program decision D36 (`program/decisions.md`).\n"
    "The repairs and limits listed under \"Changes from v1 (D36)\" and design\n"
    f"decisions 16-21 {accepted} {a} amends D36 (iii) for the\n"
    "Qwen3.5-4B-Base lane (decision 18) and authorised the second development\n"
    "timing job, whose measurement of the fixed path (Slurm 810) sets the 4B limit\n"
    f"by D36's rule (decisions 20 and 21){tail} No lane job of this experiment ran\n"
    "before the freeze; every lane job verifies this file's digest against its\n"
    "ledger row at start-up and refuses code whose SHA-256 differs from the table\n"
    "below. Both development timing jobs ran before the freeze (Compute): Slurm 766\n"
    "on the 4B path as it was before the fix (cuDNN's attention on) and Slurm 810\n"
    "on the fixed path (cuDNN's attention off).")
status = textwrap.fill(" ".join(status.split()), width=78, break_on_hyphens=False,
                       break_long_words=False)
text = text[:start] + status + text[end:]

if mode != "status-only":
    old = ("Decisions 16-21 are v2's (D36). D42 accepts them as amended by it, after a\n"
           "narrow re-check of the measured limits: decision 18's switch departs from D36\n"
           "(iii) on the 4B lane, which D42 (i) amends, and decisions 20 and 21 set the\n"
           "4B limit from the second timing job that D42 (ii) authorised. D44 closed the\n"
           "re-check, setting that limit at the largest of the estimates computed from\n"
           "the job (decision 20), and accepts decisions 16-21 as amended by D42 and D44.\n"
           "Rewriting this lead-in and the status paragraph to the frozen wording, naming\n"
           "D42 and D44, is still to be done (Freeze procedure, step 1).")
    if with_d44:
        new = (f"Decisions 16-21 are v2's (D36), accepted in {a} and D44 as amended by them,\n"
               "after a narrow re-check of the measured limits: decision 18's switch departs\n"
               f"from D36 (iii) on the 4B lane, which {a} (i) amends, and decisions 20 and 21\n"
               f"set the 4B limit from the second timing job that {a} (ii) authorised, at the\n"
               "largest of the estimates computed from it (D44).")
    else:
        new = (f"Decisions 16-21 are v2's (D36), accepted in {a} as amended by it, after a\n"
               "narrow re-check of the measured limits: decision 18's switch departs from\n"
               f"D36 (iii) on the 4B lane, which {a} (i) amends, and decisions 20 and 21 set\n"
               f"the 4B limit from the second timing job that {a} (ii) authorised.")
    assert text.count(old) == 1
    text = text.replace(old, new)
reg.write_text(text)
print(mode, "rewritten naming", a, "and D44" if with_d44 else "only")
