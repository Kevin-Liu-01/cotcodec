import numpy as np, json
exec(open('ks_power.py').read().split("scen = [")[0])
def meanD_symmetric(pa, pb, sd=1.0, seed=42, R=4000):
    rng = np.random.Generator(np.random.PCG64([seed, 5])); K = pa.shape[0]
    p0 = rng.beta(np.broadcast_to(pa, (R, K, 2)), np.broadcast_to(pb, (R, K, 2)))
    eps = rng.normal(0, sd, size=(R, K, 1))
    p1 = pw.expit(pw.logit(p0) + eps)
    return float((p1 - p0).mean())
allrows = [r for r in rows if r['class'] != 'excluded_coordinate_setup']
def post(s): return real_post(s)
out = {}
for name, s in (('selected_43', sets['LO_TB_GIMP']), ('selected_LO26', sets['LO_strict']), ('unselected_all_77', allrows), ('unselected_LO', [r for r in allrows if r['domain'].startswith('libreoffice')])):
    pa, pb = post(s)
    out[name] = {sd: round(100 * meanD_symmetric(pa, pb, sd), 2) for sd in (0.5, 1.0, 2.0)}
    print(name, len(s), out[name])
json.dump(out, open('ks_select_out.json', 'w'))
