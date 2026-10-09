"""K1 v3 repair under D52: cost of the third repair (synthesis arithmetic, not a probe).

Same rates, formula and counting rule as repair-cost-model.py (lane 862 per-unit rates, K1 v2 probe
543 scaled to 4B, native-8K factor 1.2, limits max(5, ceil(1.2 x 1.15 x P + 3)) minutes, caps summed
under D22 with the V1 extension at its worst case). Changes of the third repair, each a stated
assumption:
- the pooled pre-literal statistic, the log-retention co-statistic and the direction floor reuse the
  captured scores of the same units: no cost beyond the +5 percent the second repair already added;
- pre-step item 9 (an injected cross-script degradation of the dense target, scored on LF, PRE and M
  evidence for both targets) reuses the captured scores: +2 percent on the pre-step's selection units;
- the seed top-up (decision 81 as revised): when the sealed development seed read's 80 percent upper
  bound exceeds sigma_star, the main job checkpoints and stops before the audit read, and a top-up
  job trains seeds 45 and 46 at the frozen rate (2 targets x 8 layers x 2 seeds, 610 steps, one
  teacher forward per step), then runs the audit read with five seeds. It runs in the slot whose cap
  the V1 extension reserves; the two are exclusive (a V1 failure after a top-up is INCONCLUSIVE), so
  the slot's cap is the larger of the two and the total of caps does not change.
"""
import contextlib
import importlib.util
import io
import json
import os

spec = importlib.util.spec_from_file_location("syn", os.path.join(os.path.dirname(__file__), "synthesis-cost-model.py"))
syn = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(syn)

LF = 1.05
PRE_NULLS = 1.03 * 1.02


def design(q=230, X=10, tr=2, twins=2000, n_seeds=3, dq=20):
    out = {}
    n_idx = 2 * 3 * n_seeds
    n_ext = 2 * n_seeds
    for name, s in syn.SC.items():
        cx = 2 * X * q; mn = (1 + X) * q; ml = 200; trs = 2 * tr * q
        main_S = cx + mn + ml + trs
        st = syn.step(s, n_idx); st_e = syn.step(s, n_ext); st_top = syn.step(s, 2 * 2)
        save = syn.save_layer
        sv = 7 * syn.L * save(n_idx) * s['sm']; rd = syn.L * save(n_idx) * s['sm']; kl = 64 * s['kl']
        seed_read = (280 + 160) * s['S'] * LF
        read = main_S * s['S'] * LF
        main = 300 + 610 * st + sv + kl + rd + read + seed_read
        ext = 300 + 1220 * st_e + 13 * syn.L * save(n_ext) * s['sm'] + rd + (cx + mn + ml) * s['S'] * LF
        topup = 300 + 610 * st_top + 7 * syn.L * save(4) * s['sm'] + kl + syn.L * save(2 * 2 * 5) * s['sm'] + read
        smoke = (120 + 60 + 47 + 12 * st + 6 * st_e + 2 * syn.L * save(n_idx) * s['sm'] + 4 * s['kl']
                 + 24 * (s['SMC'] + s['S'] + s['MC']) + 24 * (s['SMCp'] + s['MCp']))
        dev = (120 + 47 + (2 * X * dq) * s['SMC'] * LF * PRE_NULLS
               + ((1 + X) * dq + (1 + X) * dq + 2 * tr * dq) * s['S'] * LF * PRE_NULLS + (2 * 2 * X * dq) * s['MC'])
        h2 = 120 + 47 + 2 * twins * s['MC']
        r0 = 120 + 60 + 40 * st + 4 * syn.L * save(n_idx) * s['sm']
        r1 = 120 + 60 + 25 * st + 2 * syn.L * save(n_idx) * s['sm']
        r2 = 120 + 60 + 15 * st + 2 * syn.L * save(n_idx) * s['sm'] + rd
        jobs = {'probe-4b': None, 'smoke': smoke, 'dev-prestep': dev, 'h2-gate': h2, 'R0': r0, 'R1': r1,
                'R2': r2, 'main': main, 'extension or seed top-up (exclusive slot)': max(ext, topup)}
        rows, tot, use = {}, 0.0, 0.0
        for j, P in jobs.items():
            if P is None:
                rows[j] = (None, 15, 0.25); tot += 0.25; use += 0.1; continue
            lm, c = syn.cap(1, P); rows[j] = (round(P / 60, 1), lm, c); tot += c
            if not j.startswith('extension'):
                use += P / 3600
        lm_e, c_e = syn.cap(1, ext); lm_t, c_t = syn.cap(1, topup)
        out[name] = dict(rows=rows, total_caps=round(tot, 2), expected_use_no_ext=round(use, 2),
                         extension=dict(minutes=round(ext / 60, 1), limit=lm_e, cap=c_e),
                         seed_topup=dict(minutes=round(topup / 60, 1), limit=lm_t, cap=c_t,
                                         added_use_when_triggered=round((topup - read) / 3600, 2)),
                         use_if_dev_stop=round(0.1 + (smoke + dev) / 3600, 2),
                         use_if_h2_stop=round(0.1 + (smoke + dev + h2) / 3600, 2))
    return out


res = {
    'third repair: 3 seeds, seed top-up in the extension slot (registered)': design(),
    'owner option: H2 gate on all 3,220 unseen CX cells': design(twins=3220),
    'owner option: five seeds at every learning rate (decision 81 wave-2 form)': design(n_seeds=5),
}
print(json.dumps(res, indent=1))
