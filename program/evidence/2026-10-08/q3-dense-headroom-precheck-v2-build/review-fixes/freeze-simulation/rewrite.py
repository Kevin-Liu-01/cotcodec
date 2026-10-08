"""Freeze-simulation text rewrites for q3-dense-headroom-precheck-v2 (scratch clones only).

Usage: rewrite.py CLONE MODE, MODE one of:
  full        status paragraph and design-decision lead-in rewritten, naming a simulated D42
              that the clone's decisions.md holds (the procedure's step 1)
  status-only only the status paragraph rewritten (the old step 1), D42 present
  wrong-dec   both rewritten but naming D41, which does not accept v2 or amend D36 (iii)
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
    f"clone): design decisions 16-21 and the limits accepted in {dec}\n"
    "(`program/decisions.md`), which amends D36 (iii) and D36's timing rule for the\n"
    "Qwen3.5-4B-Base lane (decisions 18, 20 and 21). No lane job of this experiment\n"
    "runs before the freeze; every lane job verifies this file's digest against its\n"
    "ledger row at start-up and refuses code whose SHA-256 differs from the table\n"
    "below. The one development timing job of D36 ran before the freeze, on the 4B\n"
    "path as it was before the fix (cuDNN's attention on; Compute).")
text = text[:start] + status + text[end:]

if mode in ("full", "wrong-dec"):
    old = ("Decisions 16-21 are v2's (D36) and wait for the program owner's\n"
           "acceptance before the freeze. Decisions 18 and 20 depart from D36 on the 4B\n"
           "lane (from D36 (iii) and from its timing rule), so the accepting decision\n"
           "must amend D36 there (Freeze procedure, step 1).")
    new = (f"Decisions 16-21 are v2's (D36), accepted in {dec} (FREEZE SIMULATION ONLY),\n"
           "which amends D36 (iii) (decision 18) and D36's timing rule (decisions 20\n"
           "and 21) for the 4B lane.")
    assert text.count(old) == 1
    text = text.replace(old, new)
reg.write_text(text)

if mode in ("full", "status-only"):
    log = clone / "program/decisions.md"
    log.write_text(log.read_text().rstrip("\n") + "\n\n"
                   "**D42. FREEZE SIMULATION ONLY (scratch clone; not a decision).** Stand-in\n"
                   "text so that the frozen-mode test can find an accepting decision:\n"
                   "`q3-dense-headroom-precheck-v2` decisions 16-21 and limits accepted; D36 (iii)\n"
                   "amended for the Qwen3.5-4B-Base lane (decision 18) and D36's timing rule\n"
                   "amended for it (decisions 20 and 21).\n")
print(mode, "rewritten")
