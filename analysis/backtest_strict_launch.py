import json, sys
from collections import defaultdict
from statistics import median

BRAND = sys.argv[1]
CONV = 'demo_sched' if BRAND == 'bhanzu' else 'leads'
inv = {json.loads(l)['hash']: json.loads(l) for l in open(f'{BRAND}/raw/inventory.jsonl')}
obs = json.load(open(f'{BRAND}/raw/canonical.json'))
try:
    cmap = json.load(open(f'{BRAND}/raw/concept_map.json'))
except FileNotFoundError:
    cmap = {}
val2c = {}
for f, cons in cmap.items():
    for c in cons:
        for v in c['values']: val2c[(f, v)] = c['concept']
traits_of = defaultdict(set)
for o in obs:
    traits_of[o['hash']].add(('v', o['facet'], o['value']))
    c = val2c.get((o['facet'], o['value']))
    if c: traits_of[o['hash']].add(('c', o['facet'], c))

def cpc_of(h):  # cost per conversion
    r = inv[h]
    return r['spend'] / r[CONV] if r.get(CONV) else None

def spearman(a, b):
    n = len(a)
    if n < 8: return None
    ra = sorted(range(n), key=lambda i: a[i]); rb = sorted(range(n), key=lambda i: b[i])
    xa=[0]*n; xb=[0]*n
    for r,i in enumerate(ra): xa[i]=r
    for r,i in enumerate(rb): xb[i]=r
    ma,mb=sum(xa)/n,sum(xb)/n
    num=sum((x-ma)*(y-mb) for x,y in zip(xa,xb)); den=(sum((x-ma)**2 for x in xa)*sum((y-mb)**2 for y in xb))**.5
    return num/den if den else 0

def run(split, label):
    # train: creatives that FINISHED before split (whole life in training window)
    tr = [h for h in inv if inv[h]['d1'] < split and inv[h]['spend'] > 20000 and inv[h].get(CONV) and traits_of.get(h)]
    # test: creatives that LAUNCHED after split (whole life in test window) — genuinely new
    te = [h for h in inv if inv[h]['d0'] >= split and inv[h]['spend'] > 20000 and inv[h].get(CONV) and traits_of.get(h)]
    if len(tr) < 30 or len(te) < 15:
        print(f'{label}: train {len(tr)} test {len(te)} — too small'); return
    tr_sp = sum(inv[h]['spend'] for h in tr); tr_cv = sum(inv[h][CONV] for h in tr)
    base = tr_sp / tr_cv
    th = defaultdict(list)
    for h in tr:
        for t in traits_of[h]: th[t].append(h)
    delta = {}
    for t, hs in th.items():
        sp = sum(inv[h]['spend'] for h in hs)
        if len(hs) < 8 or sp < 0.02*tr_sp: continue
        cv = sum(inv[h][CONV] for h in hs)
        if cv: delta[t] = (sp/cv)/base
    te_sp = sum(inv[h]['spend'] for h in te); te_cv = sum(inv[h][CONV] for h in te)
    te_base = te_sp/te_cv
    scored = []
    for h in te:
        ds = sorted(delta[t] for t in traits_of[h] if t in delta)
        if ds: scored.append((median(ds), cpc_of(h), inv[h]['spend'], h))
    if len(scored) < 12:
        print(f'{label}: only {len(scored)} scorable new creatives'); return
    scored.sort(key=lambda x: x[0])  # lower predicted cost first = system's picks
    n3 = max(4, len(scored)//3)
    def agg(rows):
        sp = sum(r[2] for r in rows); cv = sum(r[2]/r[1] for r in rows)
        return sp/cv
    rho = spearman([r[0] for r in scored], [r[1] for r in scored])
    picked, worst = agg(scored[:n3]), agg(scored[-n3:])
    print(f'{label}: train={len(tr)} newTest={len(scored)} | picked-third cost/conv ₹{picked:,.0f} vs worst-third ₹{worst:,.0f} vs all-new ₹{te_base:,.0f} | spearman {rho:+.2f}')

print(f'=== {BRAND}: train on creatives that ENDED before split, test on creatives that LAUNCHED after ===')
splits = ['2025-09-01','2025-11-01','2026-01-01','2026-03-01','2026-05-01','2026-06-01','2026-07-01'] if BRAND == 'guvi' else ['2026-04-01','2026-06-01','2026-07-01']
for s in splits: run(s, f'split {s}')
