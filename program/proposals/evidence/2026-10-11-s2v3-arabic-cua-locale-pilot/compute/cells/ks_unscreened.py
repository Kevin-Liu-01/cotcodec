"""Unscreened enlarged LibreOffice pool (no English GPU screen): all LO tasks incl. never-solved ones, n = 4 under 8 GPU-h.
Shows SMALL becomes reachable mainly through floor-task dilution."""
import numpy as np, json
_t = open('ks_rules.py').read(); exec(_t[:_t.index("scen = [('null_logit'")])
lo_all = [r for r in rows if r['domain'].startswith('libreoffice') and r['class'] != 'excluded_coordinate_setup']
pa0, pb0 = real_post(lo_all)  # 62 real LO tasks incl. zeros
spa, spb = synth(46, False, 45)  # 46 dev+reserve LO tasks, unscreened draws from the fitted prior
pa = np.vstack([pa0, spa]); pb = np.vstack([pb0, spb]); K = pa.shape[0]
n = n_max(K); print('K', K, 'n', n, pw.cost(K, n, SLOT_HIGH))
pm = pa / (pa + pb); print('posterior mean success', round(float(pm.mean()), 3), 'share of tasks with mean<0.05', round(float((pm.mean(1) < 0.05).mean()), 3))
rngc = np.random.Generator(np.random.PCG64([42, 800]))
bank = rngc.beta(np.broadcast_to(pa, (pw.CAL_BANK, K, 2)), np.broadcast_to(pb, (pw.CAL_BANK, K, 2)))
bank = pw.expit(pw.logit(bank) + rngc.normal(0, pw.SESSION_SD, size=(pw.CAL_BANK, 1, 1)))
out = {'K': K, 'n': n}
scen = [('null_logit', 'logit', 0.0), ('null_perturb', 'perturb', 0.0), ('flip_-5', 'flip', -0.05), ('logit_-5', 'logit', -0.05), ('logit_-2.3', 'logit', -0.023), ('flip_-2.3', 'flip', -0.023)]
for sname, st, td in scen:
    c = pw.calibrate(st, td, pw.T_TARGET, bank, 42)
    if c is None: print(sname, 'infeasible'); continue
    acc = []
    for sd in pw.SEEDS:
        D, kk, en = sim(pa, pb, st, c, n, sd * 1000 + n); acc.append(rules(D, kk, en, n))
    res = {k: round(float(np.mean([a[0][k] for a in acc])), 3) for k in acc[0][0]}
    res.update(mean_Bdown=round(float(np.mean([a[1] for a in acc])), 2), mean_B4=round(float(np.mean([a[3] for a in acc])), 2))
    out[sname] = res; print(sname, res, flush=True)
json.dump(out, open('ks_unscreened_out.json', 'w'), indent=1)
