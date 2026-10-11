"""Print the README tables from the committed merged outputs (run from this directory or pass it).

    python tables.py [DIR]    # DIR defaults to the directory of this file
"""
import json
import sys
from pathlib import Path

D = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
CALS = ["P0", "PR", "P4", "P4sf"]
ORDER = ["A-K32-S2R2","A6-K32-S6R2","B-K113-S2R1","D-K113-S3R1","C-K113-S2R2","E-K113-S4R1","F-K94-S3R2","F5-K105-S5R1","J2-9B-K113-S2R2","J-9B-K113-S4R2","J3-9B-K113-S3R3"]
data = {c: json.loads((D / f"designs-{c}.json").read_text())["cells"] for c in CALS if (D / f"designs-{c}.json").exists()}
cals = list(data)
def g(c, dn, sc): 
    x = data[c].get(f"{dn}|{sc}"); return x["summary"] if x else None
def rng(vals):
    vals = [v for v in vals if v is not None]
    if not vals: return "-"
    lo, hi = min(vals), max(vals)
    return f"{lo:.2f}" if abs(hi-lo) < 0.005 else f"{lo:.2f}-{hi:.2f}"
print("calibrations:", cals)
print("| Design | cap-min | DR2 decisive | of which Present | of which Near-eq | DR5 decisive (NO-GO) | GO | both inconclusive | δ 90% width, pp |")
print("|---|---:|---|---|---|---|---|---|---|")
for dn in ORDER:
    s = [g(c, dn, "fitted") for c in cals]
    if not any(s): continue
    cap = data[cals[0]][f"{dn}|fitted"]["cost"]["caps_min"]
    print(f"| {dn} | {cap} | {rng([x['P_DR2_decisive'] for x in s if x])} | {rng([x['DR2']['Present'] for x in s if x])} | {rng([x['DR2']['Near-equivalent'] for x in s if x])} | {rng([x['P_DR5_decisive'] for x in s if x])} | {rng([x['DR5']['GO'] for x in s if x])} | {rng([x['P_both_inconclusive'] for x in s if x])} | {rng([x['delta_ci90_width']['median']*100 for x in s if x])} |")
print()
print("| Design | piM: DR5 decisive (error) | null: DR2 Near-eq | null: DR5 NO-GO | null: false Present | 2M: DR2 decisive | 2M: GO |")
print("|---|---|---|---|---|---|---|")
for dn in ORDER:
    pm = [g(c, dn, "piM") for c in cals]; nu = [g(c, dn, "null") for c in cals]; p2 = [g(c, dn, "pi2M") for c in cals]
    if not any(pm + nu + p2): continue
    print(f"| {dn} | {rng([x['P_DR5_decisive'] for x in pm if x])} | {rng([x['DR2']['Near-equivalent'] for x in nu if x])} | {rng([x['DR5']['NO-GO'] for x in nu if x])} | {rng([x['DR2']['Present'] for x in nu if x])} | {rng([x['P_DR2_decisive'] for x in p2 if x])} | {rng([x['DR5']['GO'] for x in p2 if x])} |")
print()
for c in cals:
    t = {sc: data[c].get(f"C-K113-S2R2|{sc}", {}).get("truth") for sc in ("fitted","piM","null","pi2M")}
    t9 = {sc: data[c].get(f"J-9B-K113-S4R2|{sc}", {}).get("truth") for sc in ("fitted","piM","null","pi2M")}
    print(c, "truth pi_small/pi_9B/delta pp:", {sc: (round(v['pi_small'],3), round(v['pi_9B'],3), round(v['delta_pooled']*100,2)) for sc, v in t.items() if v}, "| 9B designs:", {sc: round(v['pi_9B'],3) for sc, v in t9.items() if v})


def f2(x):
    return f"{x:.2f}"


for path in [D / f"designs-{c}.json" for c in CALS]:
    d = json.loads(Path(path).read_text())
    cells = d["cells"]
    print(f"### {Path(path).stem}  ({d['fit']} {d['set_param']})")
    tr = {k.split('|')[1]: v["truth"] for k, v in cells.items() if k.startswith("C-K113-S2R2|")}
    print("truth (pool, all 113):", {s: (round(t['pi_small'],3), round(t['pi_9B'],3), round(t['delta_pooled']*100,2)) for s,t in tr.items()})
    print("| Design | caps min | n | fitted DR2 dec (Pres/NE) | fitted DR5 dec (NO-GO/GO) | both inconcl | piM DR5 dec | null DR2 NE / DR5 NO-GO / false Pres | 2M DR2 / GO | δ 90% width (pp) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for dn in ORDER:
        row = {s: cells.get(f"{dn}|{s}") for s in ("fitted","piM","null","pi2M")}
        if row["fitted"] is None: continue
        c = row["fitted"]["cost"]; n = row["fitted"]["summary"]["n"]
        def s(sc): return row[sc]["summary"] if row[sc] else None
        fi = s("fitted"); pm = s("piM"); nu = s("null"); p2 = s("pi2M")
        txt = f"| {dn} | {c['caps_min']} | {n} | {f2(fi['P_DR2_decisive'])} ({f2(fi['DR2']['Present'])}/{f2(fi['DR2']['Near-equivalent'])}) | {f2(fi['P_DR5_decisive'])} ({f2(fi['DR5']['NO-GO'])}/{f2(fi['DR5']['GO'])}) | {f2(fi['P_both_inconclusive'])} | "
        txt += (f"{f2(pm['P_DR5_decisive'])} | " if pm else "- | ")
        txt += (f"{f2(nu['DR2']['Near-equivalent'])} / {f2(nu['DR5']['NO-GO'])} / {f2(nu['DR2']['Present'])} | " if nu else "- | ")
        txt += (f"{f2(p2['P_DR2_decisive'])} / {f2(p2['DR5']['GO'])} | " if p2 else "- | ")
        txt += f"{fi['delta_ci90_width']['median']*100:.1f} |"
        if row["fitted"].get("caps_over_draws"): txt += f" draws>478: {row['fitted']['caps_over_draws']['P_over_478']:.2f}"
        print(txt)
    print()
