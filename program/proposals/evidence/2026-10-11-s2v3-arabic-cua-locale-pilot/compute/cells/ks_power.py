"""Kill-shot scout: is an unqualified SMALL reachable in S2 v3's enlarged pool under 8 GPU-h?
Reuses S2 v2's registered estimator and propensity model unchanged (power-osworld.py, imported)."""
import importlib.util, json, math, sys
import numpy as np
R = '/Users/kevinliu/repos/cotcodec/'
E = R + 'program/proposals/evidence/2026-10-10-s2-arabic-cua-locale/compute/repair-d68/'
spec = importlib.util.spec_from_file_location('pw', E + 'power-osworld.py'); pw = importlib.util.module_from_spec(spec); spec.loader.exec_module(pw)
rows = pw.task_screen(__import__('pathlib').Path(R + 'program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl'), __import__('pathlib').Path(R + 'program/evidence/2026-10-09/q2-stage1-prefreeze/plan/plan-a0a.json'))
sets = pw.task_sets(rows)
pj = json.load(open(E + 'power-osworld.json'))
a, b = pj['prior']['a'], pj['prior']['b']
H = pw.HARNESSES
NREP = int(sys.argv[1]) if len(sys.argv) > 1 else 400
SLOT_HIGH = 197.73

def real_post(s):
    pa = np.array([[a + r['k9_by_harness'][h] for h in H] for r in s]); pb = np.array([[b + 4 - r['k9_by_harness'][h] for h in H] for r in s]); return pa, pb

def synth(m, informative, seed):
    rng = np.random.Generator(np.random.PCG64([seed, 77]))
    pa, pb = [], []
    while len(pa) < m:
        p = rng.beta(a, b, size=2); k = rng.binomial(4, p)
        if informative and k.sum() < 1: continue
        pa.append(a + k); pb.append(b + 4 - k)
    return np.array(pa, float), np.array(pb, float)

def n_max(K, budget=8.0):
    best = None
    for n in range(2, 40, 2):
        if pw.cost(K, n, SLOT_HIGH)['registered_caps_gpu_h_incl_overlay'] <= budget: best = n
    return best

def run(name, pa, pb, n, scen):
    K = pa.shape[0]
    rngc = np.random.Generator(np.random.PCG64([42, 800]))
    bank = rngc.beta(np.broadcast_to(pa, (pw.CAL_BANK, K, 2)), np.broadcast_to(pb, (pw.CAL_BANK, K, 2)))
    bank = pw.expit(pw.logit(bank) + rngc.normal(0, pw.SESSION_SD, size=(pw.CAL_BANK, 1, 1)))
    out = {}
    for sname, st, td in scen:
        c = pw.calibrate(st, td, pw.T_TARGET, bank, 42)
        if c is None: out[sname] = None; continue
        c['target_d'] = td; c['target_t'] = pw.T_TARGET
        per = [pw.simulate_cell(sd * 1000 + n, pa, pb, st, c, n, NREP, pw.flip_matrix(sd, K)) for sd in pw.SEEDS]
        out[sname] = {k: round(float(np.mean([p[k] for p in per])), 3) for k in ('present_harm', 'present_benefit', 'small', 'small_unqualified', 'mean_breaks', 'mean_break_upper', 'inconclusive')}
    return out

scen = [('null_logit', 'logit', 0.0), ('null_perturb', 'perturb', 0.0), ('perturb_-5', 'perturb', -0.05), ('logit_-5', 'logit', -0.05), ('flip_-5', 'flip', -0.05)]
res = {'prior': [a, b], 'nrep_per_seed': NREP, 'seeds': list(pw.SEEDS), 'slot_high_s': SLOT_HIGH, 'designs': {}}
base_pa, base_pb = real_post(sets['LO_TB_GIMP'])  # 43 real informative tasks
lo_pa, lo_pb = real_post(sets['LO_strict'])        # 26
designs = []
# screened, informative: real 43 + synthetic informative extras (the enlarged pool's yield is unknown; S1a's LO yield was 30/64)
for extra in (0, 7, 13, 19, 23):
    spa, spb = synth(extra, True, 42)
    pa = np.vstack([base_pa, spa]) if extra else base_pa; pb = np.vstack([base_pb, spb]) if extra else base_pb
    designs.append((f'screened_K{43+extra}', pa, pb))
for extra in (10, 20):
    spa, spb = synth(extra, True, 43)
    designs.append((f'LOstrict_K{26+extra}', np.vstack([lo_pa, spa]), np.vstack([lo_pb, spb])))
# hypothetical larger informative pools (do not exist in OSWorld's LibreOffice set): what K would SMALL need?
for extra in (57, 77):
    spa, spb = synth(extra, True, 44)
    designs.append((f'hypothetical_K{43+extra}', np.vstack([base_pa, spa]), np.vstack([base_pb, spb])))
for name, pa, pb in designs:
    K = pa.shape[0]; n = n_max(K)
    for nn in sorted({n, 12} if K <= 50 else {n}):
        if nn is None: continue
        r = run(name, pa, pb, nn, scen)
        c = pw.cost(K, nn, SLOT_HIGH)
        res['designs'][f'{name}|n{nn}'] = {'K': K, 'n': nn, 'episodes': c['episodes'], 'cap_gpu_h': c['registered_caps_gpu_h_incl_overlay'], 'posterior_mean_success': round(float((pa/(pa+pb)).mean()), 3), 'results': r}
        print(name, 'K', K, 'n', nn, 'cap', c['registered_caps_gpu_h_incl_overlay'], json.dumps({k: (v['small_unqualified'], v['small'], v['present_harm'], v['mean_breaks']) if v else None for k, v in r.items()}), flush=True)
json.dump(res, open('ks_power_out.json', 'w'), indent=1)
