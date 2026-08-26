import json, sys
from collections import defaultdict
B = sys.argv[1]
can = json.load(open(f'{B}/raw/canonical.json'))
cmap = {}
if True:
    cm = json.load(open(f'{B}/raw/concept_map.json'))
    for f, cons in cm.items():
        for c in cons:
            for v in c['values']: cmap[(f, v)] = c['concept']
traits = defaultdict(set)
for o in can:
    traits[(o['facet'], o['value'])].add(o['hash'])
    cc = cmap.get((o['facet'], o['value']))
    if cc: traits[(o['facet'], cc)].add(o['hash'])
pats = json.load(open(f'{B}/results/patterns.json'))['patterns']
targets = [(p['facet'], p['trait']) for p in pats if p['verdict'] == 'CONFIRMED_WIN' and p['n'] >= 20]
targets = sorted(set(targets))
month = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
base = defaultdict(lambda: [0.0, 0])
h2t = defaultdict(list)
for t in targets:
    for h in traits.get(t, []): h2t[h].append(t)
for l in open(f'{B}/raw/daily.jsonl'):
    r = json.loads(l)
    m = r['daily_date'][:7]
    base[m][0] += r['sp']; base[m][1] += r['ld']
    for t in h2t.get(r['hash'], []):
        month[t][m][0] += r['sp']; month[t][m][1] += r['ld']
months = sorted(base)
out = {}
print(f"{'trait':<48}" + ''.join(f'{m[2:]:>8}' for m in months))
bl = ['baseline'] + [round(base[m][0]/base[m][1]) if base[m][1] else None for m in months]
print(f"{'BASELINE CPL':<48}" + ''.join(f"{(v if v else '-'):>8}" for v in bl[1:]))
for t in targets:
    row = []
    for m in months:
        sp, ld = month[t][m]
        row.append(round(sp/ld) if ld >= 30 else None)
    if sum(1 for v in row if v) < 4: continue
    out[f'{t[0]}:{t[1]}'] = {'monthly_cpl': dict(zip(months, row)), 'baseline': {m: (round(base[m][0]/base[m][1]) if base[m][1] else None) for m in months}}
    print(f"{t[0]+':'+t[1]:<48}" + ''.join(f"{(v if v else '-'):>8}" for v in row))
json.dump(out, open(f'{B}/results/trend_lifecycle.json', 'w'), indent=1)
