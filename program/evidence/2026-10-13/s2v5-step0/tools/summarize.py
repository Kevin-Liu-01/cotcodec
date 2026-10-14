"""Descriptive tables of S2 v5 step 0 from the committed rule's output (``step0-result.json``).

Reads only ``canary_targets_v5 analyze``'s output and the pinned module's constants; decides
nothing (the reading is ``decide``'s, copied verbatim). Per (image, app, entry): each boot's ink box
of the target word, glyph rows, derived target, q2 read-back; the boot-to-boot spread; the median
target against q2's frozen target and against the rule's reference; and each boot's fixture shift
against E's median (descriptive; the admission test uses the medians).

Usage: python3 -B summarize.py SOURCE_DIR step0-result.json OUT.json > OUT.md
"""

import json
import sys
from pathlib import Path

source, result_path, out_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(source))
from harness.s2_locale import canary_targets_v5 as R  # noqa: E402

res = json.loads(result_path.read_text())
q2 = json.loads((source / R.Q2_TARGETS).read_text())["apps"]
obs = res["observations"]


def fmt_t(t):
    if t is None:
        return "-"
    if "from" in t:
        return f"({t['from'][0]},{t['from'][1]})->({t['to'][0]},{t['to'][1]})"
    return f"({t['x']},{t['y']})"


tables = {}
lines = [f"reading: {res['reading']}  decision: {res['decision']}",
         f"exit_labels: {res['exit_labels']}", ""]
for key in [(c, a, e) for c in R.CELLS for a in R.APPS for e in R.ENTRIES]:
    c, a, e = key
    rows = sorted((o for o in obs if (o["cell"], o["app"], o["entry"]) == key),
                  key=lambda o: o["boot"])
    per = res["per_image"].get(f"{c}/{a}/{e}")
    ref_e = res["per_image"].get(f"E/{a}/{e}")
    boots = []
    for o in rows:
        m = o["measurement"] or {}
        b = {"boot": o["boot"], "seq": o["seq"], "infra": o["infra"], "pass": o["pass"],
             "text": o["text"], "measured": bool(m.get("ok"))}
        if m.get("ok"):
            b.update(target_word=m["target_word"], rows=m["rows"], target=m["target"],
                     words=m["words"])
            if ref_e:
                rw = ref_e["consensus"]
                b["shift_vs_E_median"] = {
                    "dx": [m["target_word"][i] - rw["target_word"][i] for i in (0, 1)],
                    "dy": [m["rows"][i] - rw["rows"][i] for i in (0, 1)],
                }
        else:
            b["error"] = m.get("error")
        boots.append(b)
    entry = {"boots": boots}
    if per:
        t = per["consensus"]["target"]
        entry.update(
            consensus=per["consensus"], drift=per["drift"],
            offset_vs_q2_frozen=R.max_offset(t, q2[a][e]),
            offset_vs_reference=R.max_offset(t, R.REFERENCE[(a, e)]["target"]),
        )
        if ref_e:
            rw = ref_e["consensus"]
            entry["median_shift_vs_E"] = {
                "dx": [per["consensus"]["target_word"][i] - rw["target_word"][i] for i in (0, 1)],
                "dy": [per["consensus"]["rows"][i] - rw["rows"][i] for i in (0, 1)],
            }
    tables[f"{c}/{a}/{e}"] = entry
    lines.append(f"## {c} {a} {e}")
    for b in boots:
        if b["measured"]:
            s = b.get("shift_vs_E_median", {})
            lines.append(
                f"  boot {b['boot']} seq {b['seq']}: word x {b['target_word'][0]}-"
                f"{b['target_word'][1]} rows {b['rows'][0]}-{b['rows'][1]} target "
                f"{fmt_t(b['target'])} shift-vs-E dx {s.get('dx')} dy {s.get('dy')} "
                f"pass {b['pass']} text {b['text']!r} infra {b['infra']}")
        else:
            lines.append(f"  boot {b['boot']} seq {b['seq']}: NOT MEASURED ({b.get('error')}) "
                         f"pass {b['pass']} text {b['text']!r} infra {b['infra']}")
    if per:
        lines.append(
            f"  median {fmt_t(entry['consensus']['target'])} drift {entry['drift']} "
            f"q2 {fmt_t(q2[a][e])} (offset {entry['offset_vs_q2_frozen']}) reference "
            f"{fmt_t(R.REFERENCE[(a, e)]['target'])} (offset {entry['offset_vs_reference']}) "
            f"median shift vs E {entry.get('median_shift_vs_E')}")
    lines.append("")
out_path.write_text(json.dumps({"reading": res["reading"], "decision": res["decision"],
                                "exit_labels": res["exit_labels"], "tables": tables},
                               indent=1, sort_keys=True) + "\n")
print("\n".join(lines))
