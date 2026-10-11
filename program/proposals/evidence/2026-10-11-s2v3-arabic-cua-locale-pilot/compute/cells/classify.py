import json, glob, collections, re, os
S = json.load(open('/Users/kevinliu/repos/cotcodec/program/evidence/q2-mutation/splits.json'))
split = {}
for k in ('confirm','dev','reserve'):
    for t in S[k]: split[t] = k
K1 = {'0a0faba3','15aece23','ac1b39ff','ed43c15f'}
EXCL = {'26150609','982d12a5','e2b5e914'}
a = json.load(open('osw/test_all.json'))
rows = []
for dom in ('libreoffice_calc','libreoffice_impress','libreoffice_writer','multi_apps','thunderbird','gimp'):
    for tid in a[dom]:
        p = f'osw/examples/{dom}/{tid}.json'
        t = json.load(open(p))
        ev = t.get('evaluator', {})
        funcs = ev.get('func'); funcs = funcs if isinstance(funcs, list) else [funcs]
        txt = json.dumps(t)
        cfgtxt = json.dumps(t.get('config', []))
        coord = 'pyautogui.click' in cfgtxt or 'pyautogui.moveTo' in cfgtxt
        infeas = 'infeasible' in funcs
        related = t.get('related_apps', [])
        lo_only = all(x.startswith('libreoffice') or x in ('os',) for x in related) if dom=='multi_apps' else None
        sheetname = bool(re.search(r'"Sheet ?\d"', json.dumps(ev))) 
        net = bool(re.search(r'pip install|apt(-get)? install|snap install|install-extension', txt))
        rows.append(dict(tid=tid, short=tid[:8], dom=dom, split=split.get(tid,'out'), k1=tid[:8] in K1, excl=tid[:8] in EXCL,
                         funcs=funcs, coord=coord, infeasible=infeas, related=related, lo_only=lo_only, sheetname_in_eval=sheetname, net=net,
                         instr=t.get('instruction','')[:140]))
json.dump(rows, open('lo_rows.json','w'), indent=0)
c = collections.Counter((r['dom'], r['split']) for r in rows)
for k in sorted(c): print(k, c[k])
print()
lo = [r for r in rows if r['dom'].startswith('libreoffice')]
print('LO single-app', len(lo))
print('by split', collections.Counter(r['split'] for r in lo))
print('out-of-scope LO tasks:', [(r['short'], r['dom'], r['funcs']) for r in lo if r['split']=='out'])
beyond = [r for r in lo if r['split'] in ('dev','reserve')]
print('beyond confirm (dev+reserve)', len(beyond), collections.Counter(r['dom'] for r in beyond))
print(' coord setups', sum(r['coord'] for r in beyond), ' net installs', sum(r['net'] for r in beyond), ' sheetname in evaluator', sum(r['sheetname_in_eval'] for r in beyond))
print(' func counts', collections.Counter(f for r in beyond for f in r['funcs']).most_common())
ma = [r for r in rows if r['dom']=='multi_apps' and r['split'] in ('dev','reserve') and r['lo_only']]
print('multi_apps LO(+os)-only beyond confirm', len(ma), [(r['short'], r['related'], r['funcs']) for r in ma])
