"""K1 v3 wave-1 repair: cost projection of the repaired draft (synthesis arithmetic, not a probe).

Same rates and formula as synthesis-cost-model.py (lane 862 per-unit rates, K1 v2 probe 543
scaled to 4B, native-8K factor 1.2, limits max(5, ceil(1.2 x 1.15 x P + 3)) minutes, caps
summed under D22 with the V1 extension at its worst case). Repair additions, each a stated
assumption:
- the literal-free selection (xi^LF) and the PRE evidence reuse the captured scores; one more
  top-k per selector, layer and row: +5 percent on every selection unit of the pre-step,
  the main read and the extension;
- the pre-step's literal-leaning null family (five lambdas x two targets) and kernel-literal
  selector LEXk: +3 percent on the pre-step's selection units;
- the sealed development seed read inside the main job, before the audit read: the 14
  unseen pairs' development CX and MN legs, selection only (20 questions: 280 CX + 160 MN);
- seeds: 3 (registered) or 5 (owner option), at every learning rate (one shared stream);
- CS legs: kept (wave-1 draft) or dropped (repaired draft, decision 69 revised).
"""
import json, math, importlib.util, os
spec = importlib.util.spec_from_file_location("syn", os.path.join(os.path.dirname(__file__), "synthesis-cost-model.py"))
syn = importlib.util.module_from_spec(spec)
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(syn)

LF = 1.05
PRE_NULLS = 1.03


def design(q=230, X=10, cs=5, tr=2, twins=2000, n_seeds=3, dq=20, dev_seed_read=True):
    out = {}
    n_idx = 2 * 3 * n_seeds            # targets x learning rates x seeds per layer
    n_ext = 2 * n_seeds                # the extension trains the frozen rate only
    for name, s in syn.SC.items():
        cx = 2 * X * q; mn = (1 + X) * q; ml = 200; trs = 2 * tr * q; css = (2 * cs * q + cs * q) if cs else 0
        main_S = cx + mn + ml + trs + css
        st = syn.step(s, n_idx); st_e = syn.step(s, n_ext)
        save = syn.save_layer
        sv = 7 * syn.L * save(n_idx) * s['sm']; rd = syn.L * save(n_idx) * s['sm']; kl = 64 * s['kl']
        seed_read = (280 + 160) * s['S'] * LF if dev_seed_read else 0.0
        main = 300 + 610 * st + sv + kl + rd + main_S * s['S'] * LF + seed_read
        ext = 300 + 1220 * st_e + 13 * syn.L * save(n_ext) * s['sm'] + rd + (cx + mn + ml) * s['S'] * LF
        smoke = (120 + 60 + 47 + 12 * st + 6 * st_e + 2 * syn.L * save(n_idx) * s['sm'] + 4 * s['kl']
                 + 24 * (s['SMC'] + s['S'] + s['MC']) + 24 * (s['SMCp'] + s['MCp']))
        dev = (120 + 47 + (2 * X * dq) * s['SMC'] * LF * PRE_NULLS
               + ((1 + X) * dq + (1 + X) * dq + 2 * tr * dq) * s['S'] * LF * PRE_NULLS + (2 * 2 * X * dq) * s['MC'])
        h2 = 120 + 47 + 2 * twins * s['MC']
        r0 = 120 + 60 + 40 * st + 4 * syn.L * save(n_idx) * s['sm']
        r1 = 120 + 60 + 25 * st + 2 * syn.L * save(n_idx) * s['sm']
        r2 = 120 + 60 + 15 * st + 2 * syn.L * save(n_idx) * s['sm'] + rd
        jobs = {'probe-4b': None, 'smoke': smoke, 'dev-prestep': dev, 'h2-gate': h2, 'R0': r0, 'R1': r1,
                'R2': r2, 'main': main, 'extension': ext}
        rows = {}; tot = 0.0; use = 0.0
        for j, P in jobs.items():
            if P is None:
                rows[j] = (None, 15, 0.25); tot += 0.25; use += 0.1; continue
            lm, c = syn.cap(1, P); rows[j] = (round(P / 60, 1), lm, c); tot += c
            if j != 'extension':
                use += P / 3600
        out[name] = dict(rows=rows, total_caps=round(tot, 2), expected_use_no_ext=round(use, 2),
                         ext_use=round(ext / 3600, 2), step=round(st, 2),
                         use_if_dev_stop=round(0.1 + (smoke + dev) / 3600, 2),
                         use_if_h2_stop=round(0.1 + (smoke + dev + h2) / 3600, 2))
    return out


designs = {
    'wave-1 draft (reproduced by this file with LF=1, no seed read)': None,
    'repaired: 3 seeds, CS dropped (registered)': dict(cs=0),
    'repaired: 3 seeds, CS kept': dict(cs=5),
    'repaired: 5 seeds, CS dropped (owner option)': dict(cs=0, n_seeds=5),
    'repaired: 5 seeds, CS kept': dict(cs=5, n_seeds=5),
    'repaired: 3 seeds, CS dropped, 3,220 H2 cells (all unseen CX)': dict(cs=0, twins=3220),
}
res = {}
for n, kw in designs.items():
    if kw is None:
        LF_save, PN_save = LF, PRE_NULLS
        LF = 1.0; PRE_NULLS = 1.0
        res[n] = design(dev_seed_read=False)
        LF, PRE_NULLS = LF_save, PN_save
    else:
        res[n] = design(**kw)
print(json.dumps(res, indent=1))
